from flask import Blueprint, render_template

morbidity_bp = Blueprint('morbidity', __name__, url_prefix='/reports')


@morbidity_bp.route('/proforma-ii')
def proforma_ii():
    return render_template('morbidity_report.html')
