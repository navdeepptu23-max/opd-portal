const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { Pool } = require("pg");

const HOST = process.env.HOST || "0.0.0.0";
const PORT = process.env.PORT || 3000;
const DATABASE_URL = process.env.DATABASE_URL;

if (!DATABASE_URL) {
  throw new Error("DATABASE_URL is required. Configure a Postgres database connection.");
}

const pool = new Pool({
  connectionString: DATABASE_URL,
  ssl: DATABASE_URL.includes("render.com") ? { rejectUnauthorized: false } : false,
});

const sessions = new Map();

function hashPassword(password, salt = crypto.randomBytes(16).toString("hex")) {
  const hash = crypto.pbkdf2Sync(password, salt, 120000, 32, "sha256").toString("hex");
  return { hash, salt };
}

function verifyPassword(password, hash, salt) {
  const candidate = hashPassword(password, salt).hash;
  return crypto.timingSafeEqual(Buffer.from(candidate, "hex"), Buffer.from(hash, "hex"));
}

function toSafeUser(user) {
  return {
    id: user.id,
    username: user.username,
    role: user.role,
    parentAdminId: user.parent_admin_id,
    active: user.active,
    createdAt: user.created_at,
  };
}

function sendJson(res, code, payload) {
  res.writeHead(code, {
    "Content-Type": "application/json; charset=utf-8",
  });
  res.end(JSON.stringify(payload));
}

async function dbQuery(text, params = []) {
  return pool.query(text, params);
}

async function initDatabase() {
  await dbQuery(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      username TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      password_salt TEXT NOT NULL,
      role TEXT NOT NULL CHECK (role IN ('super_admin', 'admin', 'sub')),
      parent_admin_id TEXT NULL,
      active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  await dbQuery(`
    CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_idx
    ON users ((LOWER(username)))
  `);

  const existing = await dbQuery("SELECT COUNT(*)::int AS count FROM users");
  if (existing.rows[0].count > 0) {
    return;
  }

  const { hash, salt } = hashPassword("admin123");
  await dbQuery(
    `
      INSERT INTO users (id, username, password_hash, password_salt, role, parent_admin_id, active)
      VALUES ($1, $2, $3, $4, 'super_admin', NULL, TRUE)
    `,
    [crypto.randomUUID(), "admin", hash, salt]
  );
}

async function findUserByUsername(username) {
  const result = await dbQuery("SELECT * FROM users WHERE LOWER(username) = LOWER($1) LIMIT 1", [username]);
  return result.rows[0] || null;
}

async function findUserById(id) {
  const result = await dbQuery("SELECT * FROM users WHERE id = $1 LIMIT 1", [id]);
  return result.rows[0] || null;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk.toString();
      if (body.length > 1_000_000) {
        reject(new Error("Payload too large"));
      }
    });
    req.on("end", () => {
      if (!body) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch {
        reject(new Error("Invalid JSON body"));
      }
    });
    req.on("error", reject);
  });
}

async function getAuthUser(req) {
  const auth = req.headers.authorization || "";
  if (!auth.startsWith("Bearer ")) {
    return null;
  }

  const token = auth.slice(7).trim();
  if (!token || !sessions.has(token)) {
    return null;
  }

  const session = sessions.get(token);
  const user = await findUserById(session.userId);
  if (!user || !user.active) {
    sessions.delete(token);
    return null;
  }

  return { token, user };
}

async function usernameExists(username) {
  const result = await dbQuery("SELECT 1 FROM users WHERE LOWER(username) = LOWER($1) LIMIT 1", [username]);
  return result.rowCount > 0;
}

async function canManageSubUser(authUser, subUser, adminIdFromBody) {
  if (authUser.role === "super_admin") {
    if (!adminIdFromBody) {
      return true;
    }
    return subUser.parent_admin_id === adminIdFromBody;
  }

  return subUser.parent_admin_id === authUser.id;
}

async function userIsAdminOwner(adminId) {
  const result = await dbQuery(
    "SELECT 1 FROM users WHERE id = $1 AND role IN ('admin', 'super_admin') AND active = TRUE LIMIT 1",
    [adminId]
  );
  return result.rowCount > 0;
}

function normalizeDateFields(row) {
  if (!row) {
    return row;
  }
  return {
    ...row,
    created_at: new Date(row.created_at).toISOString(),
  };
}

function withNormalizedDates(rows) {
  return rows.map(normalizeDateFields);
}

function parseRequestUrl(req) {
  return new URL(req.url, "http://localhost");
}

function serveStatic(req, res) {
  const urlPath = req.url === "/" ? "/index.html" : req.url;
  const safePath = path.normalize(urlPath).replace(/^\\.+/, "");
  const filePath = path.join(__dirname, safePath);

  if (!filePath.startsWith(__dirname)) {
    sendJson(res, 403, { message: "Forbidden" });
    return;
  }

  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    sendJson(res, 404, { message: "Not found" });
    return;
  }

  const ext = path.extname(filePath);
  const contentType =
    ext === ".html"
      ? "text/html; charset=utf-8"
      : ext === ".css"
      ? "text/css; charset=utf-8"
      : ext === ".js"
      ? "application/javascript; charset=utf-8"
      : "text/plain; charset=utf-8";

  res.writeHead(200, { "Content-Type": contentType });
  fs.createReadStream(filePath).pipe(res);
}

async function handleApi(req, res) {
  const parsed = parseRequestUrl(req);
  const pathname = parsed.pathname;
  const method = req.method;

  if (pathname === "/api/login" && method === "POST") {
    const body = await readBody(req);
    const username = String(body.username || "").trim().toLowerCase();
    const password = String(body.password || "");

    const user = await findUserByUsername(username);
    if (!user || !verifyPassword(password, user.password_hash, user.password_salt)) {
      sendJson(res, 401, { message: "Invalid username or password." });
      return;
    }

    if (!user.active) {
      sendJson(res, 403, { message: "Account is disabled." });
      return;
    }

    const token = crypto.randomBytes(24).toString("hex");
    sessions.set(token, { userId: user.id, createdAt: Date.now() });

    sendJson(res, 200, { token, user: toSafeUser(normalizeDateFields(user)) });
    return;
  }

  if (pathname === "/api/me" && method === "GET") {
    const auth = await getAuthUser(req);
    if (!auth) {
      sendJson(res, 401, { message: "Unauthorized" });
      return;
    }

    sendJson(res, 200, { user: toSafeUser(normalizeDateFields(auth.user)) });
    return;
  }

  if (pathname === "/api/logout" && method === "POST") {
    const auth = await getAuthUser(req);
    if (auth) {
      sessions.delete(auth.token);
    }
    sendJson(res, 200, { ok: true });
    return;
  }

  if (pathname === "/api/super/admins" && method === "GET") {
    const auth = await getAuthUser(req);
    if (!auth || auth.user.role !== "super_admin") {
      sendJson(res, 403, { message: "Super admin only." });
      return;
    }

    const result = await dbQuery("SELECT * FROM users WHERE role = 'admin' ORDER BY created_at DESC");
    const admins = withNormalizedDates(result.rows).map(toSafeUser);
    sendJson(res, 200, { admins });
    return;
  }

  if (pathname === "/api/super/admins" && method === "POST") {
    const auth = await getAuthUser(req);
    if (!auth || auth.user.role !== "super_admin") {
      sendJson(res, 403, { message: "Super admin only." });
      return;
    }

    const body = await readBody(req);
    const username = String(body.username || "").trim();
    const password = String(body.password || "").trim();

    if (username.length < 3 || password.length < 4) {
      sendJson(res, 400, { message: "Username/password too short." });
      return;
    }

    const exists = await usernameExists(username);
    if (exists) {
      sendJson(res, 409, { message: "Username already exists." });
      return;
    }

    const { hash, salt } = hashPassword(password);
    await dbQuery(
      `
        INSERT INTO users (id, username, password_hash, password_salt, role, parent_admin_id, active)
        VALUES ($1, $2, $3, $4, 'admin', NULL, TRUE)
      `,
      [crypto.randomUUID(), username, hash, salt]
    );

    sendJson(res, 201, { ok: true });
    return;
  }

  const superToggleMatch = pathname.match(/^\/api\/super\/admins\/([^/]+)\/toggle$/);
  if (superToggleMatch && method === "PATCH") {
    const auth = await getAuthUser(req);
    if (!auth || auth.user.role !== "super_admin") {
      sendJson(res, 403, { message: "Super admin only." });
      return;
    }

    const adminId = superToggleMatch[1];
    const result = await dbQuery("SELECT * FROM users WHERE id = $1 AND role = 'admin' LIMIT 1", [adminId]);
    const admin = result.rows[0];
    if (!admin) {
      sendJson(res, 404, { message: "Admin not found." });
      return;
    }

    const nextActive = !admin.active;
    await dbQuery("UPDATE users SET active = $1 WHERE id = $2", [nextActive, admin.id]);
    sendJson(res, 200, { ok: true, active: nextActive });
    return;
  }

  if (pathname === "/api/admin/sub-logins" && method === "GET") {
    const auth = await getAuthUser(req);
    if (!auth || (auth.user.role !== "admin" && auth.user.role !== "super_admin")) {
      sendJson(res, 403, { message: "Admin only." });
      return;
    }

    const adminIdQuery = parsed.searchParams.get("adminId");
    const targetAdminId = auth.user.role === "super_admin" ? adminIdQuery || auth.user.id : auth.user.id;

    const result = await dbQuery(
      "SELECT * FROM users WHERE role = 'sub' AND parent_admin_id = $1 ORDER BY created_at DESC",
      [targetAdminId]
    );
    const subUsers = withNormalizedDates(result.rows).map(toSafeUser);
    sendJson(res, 200, { subUsers });
    return;
  }

  if (pathname === "/api/admin/sub-logins" && method === "POST") {
    const auth = await getAuthUser(req);
    if (!auth || (auth.user.role !== "admin" && auth.user.role !== "super_admin")) {
      sendJson(res, 403, { message: "Admin only." });
      return;
    }

    const body = await readBody(req);
    const username = String(body.username || "").trim();
    const password = String(body.password || "").trim();

    const requestedAdminId = String(body.adminId || "").trim();
    const ownerAdminId = auth.user.role === "super_admin" ? requestedAdminId || auth.user.id : auth.user.id;

    if (username.length < 3 || password.length < 4) {
      sendJson(res, 400, { message: "Username/password too short." });
      return;
    }

    const ownerExists = await userIsAdminOwner(ownerAdminId);
    if (!ownerExists) {
      sendJson(res, 400, { message: "Owner admin not found." });
      return;
    }

    const exists = await usernameExists(username);
    if (exists) {
      sendJson(res, 409, { message: "Username already exists." });
      return;
    }

    const { hash, salt } = hashPassword(password);
    await dbQuery(
      `
        INSERT INTO users (id, username, password_hash, password_salt, role, parent_admin_id, active)
        VALUES ($1, $2, $3, $4, 'sub', $5, TRUE)
      `,
      [crypto.randomUUID(), username, hash, salt, ownerAdminId]
    );

    sendJson(res, 201, { ok: true });
    return;
  }

  const subToggleMatch = pathname.match(/^\/api\/admin\/sub-logins\/([^/]+)\/toggle$/);
  if (subToggleMatch && method === "PATCH") {
    const auth = await getAuthUser(req);
    if (!auth || (auth.user.role !== "admin" && auth.user.role !== "super_admin")) {
      sendJson(res, 403, { message: "Admin only." });
      return;
    }

    const body = await readBody(req);
    const userId = subToggleMatch[1];
    const result = await dbQuery("SELECT * FROM users WHERE id = $1 AND role = 'sub' LIMIT 1", [userId]);
    const managedUser = result.rows[0];

    if (!managedUser) {
      sendJson(res, 404, { message: "Sub user not found." });
      return;
    }

    const adminIdFromBody = String(body.adminId || "").trim();
    const canManage = await canManageSubUser(auth.user, managedUser, adminIdFromBody);
    if (!canManage) {
      sendJson(res, 403, { message: "You cannot manage this user." });
      return;
    }

    const nextActive = !managedUser.active;
    await dbQuery("UPDATE users SET active = $1 WHERE id = $2", [nextActive, managedUser.id]);
    sendJson(res, 200, { ok: true, active: nextActive });
    return;
  }

  const subPassMatch = pathname.match(/^\/api\/admin\/sub-logins\/([^/]+)\/password$/);
  if (subPassMatch && method === "PATCH") {
    const auth = await getAuthUser(req);
    if (!auth || (auth.user.role !== "admin" && auth.user.role !== "super_admin")) {
      sendJson(res, 403, { message: "Admin only." });
      return;
    }

    const body = await readBody(req);
    const userId = subPassMatch[1];
    const result = await dbQuery("SELECT * FROM users WHERE id = $1 AND role = 'sub' LIMIT 1", [userId]);
    const managedUser = result.rows[0];

    if (!managedUser) {
      sendJson(res, 404, { message: "Sub user not found." });
      return;
    }

    const password = String(body.password || "").trim();
    if (password.length < 4) {
      sendJson(res, 400, { message: "Password too short." });
      return;
    }

    const adminIdFromBody = String(body.adminId || "").trim();
    const canManage = await canManageSubUser(auth.user, managedUser, adminIdFromBody);
    if (!canManage) {
      sendJson(res, 403, { message: "You cannot manage this user." });
      return;
    }

    const { hash, salt } = hashPassword(password);
    await dbQuery("UPDATE users SET password_hash = $1, password_salt = $2 WHERE id = $3", [
      hash,
      salt,
      managedUser.id,
    ]);
    sendJson(res, 200, { ok: true });
    return;
  }

  const subDeleteMatch = pathname.match(/^\/api\/admin\/sub-logins\/([^/]+)$/);
  if (subDeleteMatch && method === "DELETE") {
    const auth = await getAuthUser(req);
    if (!auth || (auth.user.role !== "admin" && auth.user.role !== "super_admin")) {
      sendJson(res, 403, { message: "Admin only." });
      return;
    }

    const body = await readBody(req);
    const userId = subDeleteMatch[1];
    const result = await dbQuery("SELECT * FROM users WHERE id = $1 AND role = 'sub' LIMIT 1", [userId]);
    const managedUser = result.rows[0];
    if (!managedUser) {
      sendJson(res, 404, { message: "Sub user not found." });
      return;
    }

    const adminIdFromBody = String(body.adminId || "").trim();
    const canManage = await canManageSubUser(auth.user, managedUser, adminIdFromBody);
    if (!canManage) {
      sendJson(res, 403, { message: "You cannot manage this user." });
      return;
    }

    await dbQuery("DELETE FROM users WHERE id = $1", [managedUser.id]);
    sendJson(res, 200, { ok: true });
    return;
  }

  sendJson(res, 404, { message: "Not found" });
}

async function start() {
  await initDatabase();

  const server = http.createServer(async (req, res) => {
    try {
      if (req.url.startsWith("/api/")) {
        await handleApi(req, res);
        return;
      }

      if (req.method !== "GET") {
        sendJson(res, 405, { message: "Method not allowed" });
        return;
      }

      serveStatic(req, res);
    } catch (error) {
      sendJson(res, 500, { message: error.message || "Server error" });
    }
  });

  server.listen(PORT, HOST, () => {
    console.log(`Portal running at http://${HOST}:${PORT}`);
  });
}

start().catch((error) => {
  console.error("Failed to start server:", error.message);
  process.exit(1);
});
