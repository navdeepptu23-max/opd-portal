import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from modules.morbidity import morbidity_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-in-production-use-env-var')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///portal.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
app.register_blueprint(morbidity_bp)

HOSPITAL_INDICATOR_DEFAULTS = [
    (1, 'Total OPD Attendance'),
    (2, 'Total IPD Admissions'),
    (3, 'Emergency Cases Handled'),
    (4, 'Maternal Cases Registered'),
    (5, 'Institutional Deliveries'),
    (6, 'Immunization Sessions Conducted'),
    (7, 'Lab Tests Performed'),
    (8, 'Referral Cases Sent'),
    (9, 'Referral Cases Received'),
    (10, 'Road Traffic Accident Cases'),
]

PROFORMA_HPI_DEFAULTS = [
    ('1A', 'NO. OF OUTPATIENTS: NEW'),
    ('1B', 'OLD'),
    ('1C', 'EMERGENCY'),
    ('1D', 'TOTAL'),
    ('2', 'NO OF ADMISSIONS DURING THE MONTH'),
    ('3', 'NO. OF ADMISSIONS THROUGH EMERGENCY (OUT OF 2)'),
    ('4', 'NO. OF MEDICAL LEGAL CASES ADMITTED (OUT OF 2)'),
    ('5', 'NO. OF PATIENTS ADMITTED AND DISCHARGED ON THE SAME DAY (OUT OF 2)'),
    ('6', 'NO. OF TUBECTOMIES INCLUDING LAPAROSCOPIC'),
    ('7', 'NO OF VASECTOMIES'),
    ('8', 'NO. OF MINOR SURGERIES (EXCLUDING VASECTOMIES)'),
    ('9', 'NO. OF MAJOR SURGERIES (EXCLUDING TUBECTOMIES)'),
    ('10', 'TOTAL NO. OF SURGERIES (5+6+7+8)'),
    ('11', 'NO. OF DEATHS (Please mention no of maternal and infant hospital deaths in remarks column separately)'),
    ('13', 'NO. OF NORMAL DELIVERIES'),
    ('14', 'NO. OF CAESAREAN DELIVERIES'),
    ('15', 'TOTAL NO. OF DELIVERIES (13+14)'),
    ('16', 'MALE CH (EXCLUDING STILL BIRTH OUT OF 15)'),
    ('17', 'FEMALE CH (EXCLUDING STILL BIRTH OUT OF 15)'),
    ('21', 'NO. OF LAB-TESTS'),
    ('22', 'TOTAL NO. OF CUMULATIVE INPATIENTS DAYS'),
    ('23', 'User Charges Collection during the month (in Rs.)'),
    ('24', 'Number of RSBY Cases during the month'),
]

PROFORMA_HPI_ORDER = {code: index for index, (code, _) in enumerate(PROFORMA_HPI_DEFAULTS)}


# ── Models ──────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id          = db.Column(db.Integer, primary_key=True)
    username    = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role        = db.Column(db.String(20), nullable=False, default='sub')
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    is_active   = db.Column(db.Boolean, default=True)

    creator     = db.relationship('User', remote_side=[id], backref='created_users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    @property
    def is_admin_or_above(self):
        return self.role in ('super_admin', 'admin')

    def can_manage(self, target_user):
        """Return True if this user has permission to manage target_user."""
        if self.is_super_admin:
            return target_user.id != self.id
        if self.role == 'admin':
            return target_user.created_by == self.id
        return False


class HospitalIndicator(db.Model):
    __tablename__ = 'hospital_indicators'

    id = db.Column(db.Integer, primary_key=True)
    month_year = db.Column(db.String(20), nullable=False, index=True)
    indicator_no = db.Column(db.Integer, nullable=False)
    indicator_name = db.Column(db.String(180), nullable=False)
    opd_count = db.Column(db.Integer, nullable=False, default=0)
    ipd_count = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('month_year', 'indicator_no', name='uq_hospital_indicator_month_no'),
    )


class HospitalIndicatorMeta(db.Model):
    __tablename__ = 'hospital_indicator_meta'

    id = db.Column(db.Integer, primary_key=True)
    month_year = db.Column(db.String(20), nullable=False, unique=True, index=True)
    institution_name = db.Column(db.String(150), nullable=False, default='PHC POSSI')


class ProformaHPIRow(db.Model):
    __tablename__ = 'proforma_hpi_rows'

    id = db.Column(db.Integer, primary_key=True)
    month_year = db.Column(db.String(20), nullable=False, index=True)
    indicator_code = db.Column(db.String(8), nullable=False)
    indicator_label = db.Column(db.String(260), nullable=False)
    male = db.Column(db.Integer, nullable=False, default=0)
    female = db.Column(db.Integer, nullable=False, default=0)
    male_child_u14 = db.Column(db.Integer, nullable=False, default=0)
    female_child_u14 = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False, default=0)
    remarks = db.Column(db.String(260), nullable=False, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('month_year', 'indicator_code', name='uq_proforma_hpi_month_code'),
    )


class ProformaHPIMeta(db.Model):
    __tablename__ = 'proforma_hpi_meta'

    id = db.Column(db.Integer, primary_key=True)
    month_year = db.Column(db.String(20), nullable=False, unique=True, index=True)
    hospital_name = db.Column(db.String(200), nullable=False, default='COMPILED REPORT OF BLOCK- POSSI')
    district = db.Column(db.String(120), nullable=False, default='HOSHIARPUR')
    sanctioned_beds = db.Column(db.String(60), nullable=False, default='')
    functional_beds = db.Column(db.String(60), nullable=False, default='')
    doctor_incharge = db.Column(db.String(120), nullable=False, default='SMO POSSI')
    note_text = db.Column(
        db.String(400),
        nullable=False,
        default='Comments of SMO incharge regarding change of functional beds if any, nil reports and unusually large or small comparative figures regarding performance of any department of the hospital should be mentioned in the remarks column.'
    )


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Forms ────────────────────────────────────────────────────────────────────

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Sign In')


class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm  = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    role     = SelectField('Role', choices=[('sub', 'Sub User'), ('admin', 'Admin')])
    submit   = SubmitField('Create User')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')


class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    submit   = SubmitField('Save Changes')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user and user.id != current_user.id:
            raise ValidationError('Username already taken.')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password     = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm          = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match.')])
    submit           = SubmitField('Update Password')


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if current_user.is_authenticated else render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/help')
def help_page():
    return render_template('help.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


def _to_non_negative_int(value):
    try:
        return max(0, int(str(value).strip()))
    except (ValueError, TypeError):
        return 0


def _ensure_hospital_indicator_rows(month_year):
    existing_count = HospitalIndicator.query.filter_by(month_year=month_year).count()
    if existing_count == 0:
        for number, name in HOSPITAL_INDICATOR_DEFAULTS:
            db.session.add(HospitalIndicator(
                month_year=month_year,
                indicator_no=number,
                indicator_name=name,
                opd_count=0,
                ipd_count=0,
            ))
        db.session.commit()

    meta = HospitalIndicatorMeta.query.filter_by(month_year=month_year).first()
    if not meta:
        meta = HospitalIndicatorMeta(month_year=month_year, institution_name='PHC POSSI')
        db.session.add(meta)
        db.session.commit()


def _ensure_proforma_hpi_rows(month_year):
    existing_count = ProformaHPIRow.query.filter_by(month_year=month_year).count()
    if existing_count == 0:
        for code, label in PROFORMA_HPI_DEFAULTS:
            db.session.add(ProformaHPIRow(
                month_year=month_year,
                indicator_code=code,
                indicator_label=label,
                male=0,
                female=0,
                male_child_u14=0,
                female_child_u14=0,
                total=0,
                remarks='',
            ))
        db.session.commit()

    meta = ProformaHPIMeta.query.filter_by(month_year=month_year).first()
    if not meta:
        db.session.add(ProformaHPIMeta(month_year=month_year))
        db.session.commit()


@app.route('/reports/hospital-indicator', methods=['GET', 'POST'])
@login_required
def hospital_indicator_report():
    month_year = (request.values.get('month_year') or datetime.utcnow().strftime('%b-%Y')).upper()
    _ensure_hospital_indicator_rows(month_year)

    if request.method == 'POST':
        if not current_user.is_admin_or_above:
            abort(403)

        institution_name = (request.form.get('institution_name') or 'PHC POSSI').strip() or 'PHC POSSI'
        meta = HospitalIndicatorMeta.query.filter_by(month_year=month_year).first()
        meta.institution_name = institution_name[:150]

        indicators = HospitalIndicator.query.filter_by(month_year=month_year).order_by(HospitalIndicator.indicator_no.asc()).all()
        for item in indicators:
            item.opd_count = _to_non_negative_int(request.form.get(f'opd_{item.id}', 0))
            item.ipd_count = _to_non_negative_int(request.form.get(f'ipd_{item.id}', 0))

        db.session.commit()
        flash('Hospital Indicator Report updated successfully.', 'success')
        return redirect(url_for('hospital_indicator_report', month_year=month_year))

    meta = HospitalIndicatorMeta.query.filter_by(month_year=month_year).first()
    indicators = HospitalIndicator.query.filter_by(month_year=month_year).order_by(HospitalIndicator.indicator_no.asc()).all()
    total_opd = sum(item.opd_count for item in indicators)
    total_ipd = sum(item.ipd_count for item in indicators)

    return render_template(
        'hospital_indicator_report.html',
        month_year=month_year,
        institution_name=meta.institution_name,
        indicators=indicators,
        total_opd=total_opd,
        total_ipd=total_ipd,
    )


@app.route('/reports/proforma-i-hpi', methods=['GET', 'POST'])
@login_required
def proforma_i_hpi_report():
    month_year = (request.values.get('month_year') or 'MAR-2026').upper()
    _ensure_proforma_hpi_rows(month_year)

    if request.method == 'POST':
        if not current_user.is_admin_or_above:
            abort(403)

        meta = ProformaHPIMeta.query.filter_by(month_year=month_year).first()
        meta.hospital_name = (request.form.get('hospital_name') or '').strip()[:200] or 'COMPILED REPORT OF BLOCK- POSSI'
        meta.district = (request.form.get('district') or '').strip()[:120] or 'HOSHIARPUR'
        meta.sanctioned_beds = (request.form.get('sanctioned_beds') or '').strip()[:60]
        meta.functional_beds = (request.form.get('functional_beds') or '').strip()[:60]
        meta.doctor_incharge = (request.form.get('doctor_incharge') or '').strip()[:120] or 'SMO POSSI'
        meta.note_text = (request.form.get('note_text') or '').strip()[:400] or meta.note_text

        rows = ProformaHPIRow.query.filter_by(month_year=month_year).all()
        rows.sort(key=lambda r: PROFORMA_HPI_ORDER.get(r.indicator_code, 9999))
        _single_codes = {'13', '14', '15', '16', '17', '21', '22', '23', '24'}
        for row in rows:
            if row.indicator_code in _single_codes:
                row.male = 0
                row.female = 0
                row.male_child_u14 = 0
                row.female_child_u14 = 0
                row.total = _to_non_negative_int(request.form.get(f'single_{row.id}', 0))
            else:
                row.male = _to_non_negative_int(request.form.get(f'male_{row.id}', 0))
                row.female = _to_non_negative_int(request.form.get(f'female_{row.id}', 0))
                row.male_child_u14 = _to_non_negative_int(request.form.get(f'male_child_{row.id}', 0))
                row.female_child_u14 = _to_non_negative_int(request.form.get(f'female_child_{row.id}', 0))
                row.total = row.male + row.female + row.male_child_u14 + row.female_child_u14
            row.remarks = (request.form.get(f'remarks_{row.id}') or '').strip()[:260]
        # Row 15 = Row 13 + Row 14
        _by_code = {r.indicator_code: r for r in rows}
        if '15' in _by_code and '13' in _by_code and '14' in _by_code:
            _by_code['15'].total = _by_code['13'].total + _by_code['14'].total

        db.session.commit()
        flash('PROFORMA-I HPI report saved successfully.', 'success')
        return redirect(url_for('proforma_i_hpi_report', month_year=month_year))

    meta = ProformaHPIMeta.query.filter_by(month_year=month_year).first()
    rows = ProformaHPIRow.query.filter_by(month_year=month_year).all()
    rows.sort(key=lambda r: PROFORMA_HPI_ORDER.get(r.indicator_code, 9999))

    return render_template(
        'proforma_i_hpi_report.html',
        month_year=month_year,
        meta=meta,
        rows=rows,
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next', '')
            # Guard against open redirect
            if next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin_or_above:
        abort(403)
    form = CreateUserForm()
    # Only super_admin may create other admins
    if not current_user.is_super_admin:
        form.role.choices = [('sub', 'Sub User')]
    if form.validate_on_submit():
        new_user = User(
            username=form.username.data,
            role=form.role.data,
            created_by=current_user.id
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash(f'User "{new_user.username}" created successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('register.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_super_admin:
        users = User.query.filter(User.id != current_user.id).order_by(User.created_at.desc()).all()
    elif current_user.role == 'admin':
        users = User.query.filter_by(created_by=current_user.id).order_by(User.created_at.desc()).all()
    else:
        users = []
    search = request.args.get('q', '').strip()
    if search:
        users = [u for u in users if search.lower() in u.username.lower()]
    return render_template('dashboard.html', users=users, search=search)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.username = form.username.data
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', form=form)


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('profile'))
    return render_template('change_password.html', form=form)


@app.route('/user/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_user(user_id):
    if not current_user.is_admin_or_above:
        abort(403)
    user = User.query.get_or_404(user_id)
    if not current_user.can_manage(user):
        abort(403)
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User "{user.username}" {status}.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin_or_above:
        abort(403)
    user = User.query.get_or_404(user_id)
    if not current_user.can_manage(user):
        abort(403)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{username}" deleted.', 'success')
    return redirect(url_for('dashboard'))


# ── Error Handlers ────────────────────────────────────────────────────────────

@app.errorhandler(403)
def forbidden(e):
    return render_template('404.html', code=403, title='Forbidden',
                           message='You do not have permission to access this page.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html', code=404, title='Page Not Found',
                           message='The page you are looking for does not exist.'), 404


@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return render_template('500.html'), 500


# ── Startup ───────────────────────────────────────────────────────────────────

def seed_admin():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='super_admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Default admin created  →  admin / admin123')


with app.app_context():
    seed_admin()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
