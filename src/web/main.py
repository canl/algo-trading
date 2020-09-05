from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)


@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html', name=current_user.name)


@main.route('/perf/<env>/<account>')
@login_required
def account_performance(env: str, account: str):
    start_from = request.args.get('start_from', default=0, type=int)
    return render_template('performance.html', env=env, account=account, start_from=start_from, name=current_user.name)


@main.route('/trading-view')
def trading_view():
    return render_template('trading_view.html')


@main.route('/widgets')
def widgets():
    return render_template('widgets.html')
