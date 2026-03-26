const TOKEN_KEY = "portal_token_v2";
const ROLE = {
  SUPER_ADMIN: "super_admin",
  ADMIN: "admin",
  SUB: "sub",
};

const loginPanel = document.getElementById("loginPanel");
const dashboardPanel = document.getElementById("dashboardPanel");
const loginForm = document.getElementById("loginForm");
const loginMessage = document.getElementById("loginMessage");
const logoutBtn = document.getElementById("logoutBtn");

const dashboardTitle = document.getElementById("dashboardTitle");
const dashboardSubtitle = document.getElementById("dashboardSubtitle");

const superAdminView = document.getElementById("superAdminView");
const adminView = document.getElementById("adminView");
const subUserView = document.getElementById("subUserView");

const adminCreateForm = document.getElementById("adminCreateForm");
const superAdminMessage = document.getElementById("superAdminMessage");
const adminList = document.getElementById("adminList");

const subLoginForm = document.getElementById("subLoginForm");
const adminMessage = document.getElementById("adminMessage");
const subLoginTableBody = document.getElementById("subLoginTableBody");

const statTotal = document.getElementById("statTotal");
const statActive = document.getElementById("statActive");
const statDisabled = document.getElementById("statDisabled");

const searchSubUsers = document.getElementById("searchSubUsers");
const statusFilter = document.getElementById("statusFilter");

const appState = {
  token: localStorage.getItem(TOKEN_KEY),
  currentUser: null,
  selectedAdminId: null,
  subUsers: [],
};

function formatDate(isoDate) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(isoDate));
}

function setMessage(el, text, isError = false) {
  if (!el) {
    return;
  }
  el.textContent = text;
  el.style.color = isError ? "#b91c1c" : "#115e59";
}

function authHeaders() {
  return appState.token ? { Authorization: `Bearer ${appState.token}` } : {};
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(payload?.message || "Request failed");
  }

  return payload;
}

async function tryRestoreSession() {
  if (!appState.token) {
    renderGuest();
    return;
  }

  try {
    const data = await api("/api/me");
    appState.currentUser = data.user;
    await renderApp();
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    appState.token = null;
    appState.currentUser = null;
    renderGuest();
  }
}

function renderGuest() {
  loginPanel.classList.remove("hidden");
  dashboardPanel.classList.add("hidden");
}

async function loadSubUsers() {
  const query = appState.selectedAdminId ? `?adminId=${encodeURIComponent(appState.selectedAdminId)}` : "";
  const data = await api(`/api/admin/sub-logins${query}`);
  appState.subUsers = data.subUsers || [];
  renderSubTable();
  updateStats();
}

async function loadAdmins() {
  if (appState.currentUser?.role !== ROLE.SUPER_ADMIN) {
    return;
  }

  const data = await api("/api/super/admins");
  adminList.innerHTML = "";

  if (!data.admins.length) {
    adminList.innerHTML = "<p class=\"small-note\">No admins created yet.</p>";
    return;
  }

  data.admins.forEach((admin) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `
      <div>
        <strong>${admin.username}</strong>
        <p class="small-note">Created ${formatDate(admin.createdAt)}</p>
      </div>
      <div class="actions">
        <button class="btn btn-small" data-admin-action="select" data-id="${admin.id}">Manage</button>
        <button class="btn btn-small" data-admin-action="toggle" data-id="${admin.id}">${
      admin.active ? "Disable" : "Enable"
    }</button>
      </div>
    `;
    adminList.appendChild(item);
  });
}

function updateStats() {
  statTotal.textContent = String(appState.subUsers.length);
  statActive.textContent = String(appState.subUsers.filter((u) => u.active).length);
  statDisabled.textContent = String(appState.subUsers.filter((u) => !u.active).length);
}

function renderSubTable() {
  const search = (searchSubUsers.value || "").trim().toLowerCase();
  const status = statusFilter.value;

  const filtered = appState.subUsers.filter((user) => {
    const matchesSearch = user.username.toLowerCase().includes(search);
    const matchesStatus =
      status === "all" || (status === "active" && user.active) || (status === "disabled" && !user.active);
    return matchesSearch && matchesStatus;
  });

  subLoginTableBody.innerHTML = "";

  if (!filtered.length) {
    subLoginTableBody.innerHTML = '<tr><td colspan="4">No matching sub logins found.</td></tr>';
    return;
  }

  filtered.forEach((user) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${user.username}</td>
      <td><span class="pill ${user.active ? "active" : "disabled"}">${
      user.active ? "Active" : "Disabled"
    }</span></td>
      <td>${formatDate(user.createdAt)}</td>
      <td>
        <div class="actions">
          <button class="btn btn-small" data-action="toggle" data-id="${user.id}">${
      user.active ? "Disable" : "Enable"
    }</button>
          <button class="btn btn-small" data-action="reset" data-id="${user.id}">Reset Pass</button>
          <button class="btn btn-small btn-danger" data-action="delete" data-id="${user.id}">Delete</button>
        </div>
      </td>
    `;
    subLoginTableBody.appendChild(row);
  });
}

async function renderApp() {
  loginPanel.classList.add("hidden");
  dashboardPanel.classList.remove("hidden");

  const current = appState.currentUser;
  dashboardTitle.textContent = `Welcome, ${current.username}`;

  superAdminView.classList.add("hidden");
  adminView.classList.add("hidden");
  subUserView.classList.add("hidden");

  if (current.role === ROLE.SUB) {
    dashboardSubtitle.textContent = "You are logged in as a sub user.";
    subUserView.classList.remove("hidden");
    return;
  }

  adminView.classList.remove("hidden");

  if (current.role === ROLE.SUPER_ADMIN) {
    dashboardSubtitle.textContent = "Create admins and manage each admin's sub logins.";
    superAdminView.classList.remove("hidden");
    await loadAdmins();
    if (!appState.selectedAdminId) {
      appState.selectedAdminId = current.id;
    }
  } else {
    dashboardSubtitle.textContent = "Manage your sub logins and monitor account status.";
    appState.selectedAdminId = current.id;
  }

  await loadSubUsers();
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
      headers: {},
    });

    appState.token = data.token;
    appState.currentUser = data.user;
    localStorage.setItem(TOKEN_KEY, data.token);
    loginForm.reset();
    setMessage(loginMessage, "");
    await renderApp();
  } catch (error) {
    setMessage(loginMessage, error.message, true);
  }
});

logoutBtn.addEventListener("click", async () => {
  try {
    if (appState.token) {
      await api("/api/logout", { method: "POST" });
    }
  } catch {
    // no-op: user session is being cleared locally regardless of API result
  }

  appState.token = null;
  appState.currentUser = null;
  appState.selectedAdminId = null;
  appState.subUsers = [];
  localStorage.removeItem(TOKEN_KEY);
  setMessage(adminMessage, "");
  setMessage(superAdminMessage, "");
  renderGuest();
});

subLoginForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const subUsername = document.getElementById("subUsername").value.trim();
  const subPassword = document.getElementById("subPassword").value.trim();

  try {
    await api("/api/admin/sub-logins", {
      method: "POST",
      body: JSON.stringify({
        username: subUsername,
        password: subPassword,
        adminId: appState.selectedAdminId,
      }),
    });

    subLoginForm.reset();
    setMessage(adminMessage, `Sub login ${subUsername} created.`);
    await loadSubUsers();
  } catch (error) {
    setMessage(adminMessage, error.message, true);
  }
});

if (adminCreateForm) {
  adminCreateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("adminUsername").value.trim();
    const password = document.getElementById("adminPassword").value.trim();

    try {
      await api("/api/super/admins", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      adminCreateForm.reset();
      setMessage(superAdminMessage, `Admin ${username} created.`);
      await loadAdmins();
    } catch (error) {
      setMessage(superAdminMessage, error.message, true);
    }
  });
}

if (adminList) {
  adminList.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const action = target.dataset.adminAction;
    const adminId = target.dataset.id;

    if (!action || !adminId) {
      return;
    }

    try {
      if (action === "select") {
        appState.selectedAdminId = adminId;
        setMessage(adminMessage, "Managing selected admin sub-logins.");
        await loadSubUsers();
        return;
      }

      if (action === "toggle") {
        await api(`/api/super/admins/${adminId}/toggle`, { method: "PATCH" });
        setMessage(superAdminMessage, "Admin status updated.");
        await loadAdmins();
      }
    } catch (error) {
      setMessage(superAdminMessage, error.message, true);
    }
  });
}

subLoginTableBody.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  const action = target.dataset.action;
  const userId = target.dataset.id;
  if (!action || !userId) {
    return;
  }

  try {
    if (action === "toggle") {
      await api(`/api/admin/sub-logins/${userId}/toggle`, {
        method: "PATCH",
        body: JSON.stringify({ adminId: appState.selectedAdminId }),
      });
      setMessage(adminMessage, "User status updated.");
    }

    if (action === "reset") {
      const nextPassword = prompt("Set new password:");
      if (!nextPassword || nextPassword.trim().length < 4) {
        setMessage(adminMessage, "Password reset cancelled or too short.", true);
        return;
      }
      await api(`/api/admin/sub-logins/${userId}/password`, {
        method: "PATCH",
        body: JSON.stringify({
          adminId: appState.selectedAdminId,
          password: nextPassword.trim(),
        }),
      });
      setMessage(adminMessage, "Password updated.");
    }

    if (action === "delete") {
      const confirmed = confirm("Delete this user?");
      if (!confirmed) {
        return;
      }
      await api(`/api/admin/sub-logins/${userId}`, {
        method: "DELETE",
        body: JSON.stringify({ adminId: appState.selectedAdminId }),
      });
      setMessage(adminMessage, "Sub user deleted.");
    }

    await loadSubUsers();
  } catch (error) {
    setMessage(adminMessage, error.message, true);
  }
});

searchSubUsers.addEventListener("input", renderSubTable);
statusFilter.addEventListener("change", renderSubTable);

tryRestoreSession();
