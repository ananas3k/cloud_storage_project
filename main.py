from flask import Flask, render_template, session, make_response, redirect, jsonify, request, send_file
from data import db_session
from data.users import User
import os

from forms.user import RegisterForm, LoginForm
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)

# задаётся вручную
PATH_TO_STORAGE = 'C:/files'

def main():
    db_session.global_init("db/database.db")
    app.run()



def add_user(name, about, email):
    user = User()
    user.name = name
    user.about = about
    user.email = email
    db_sess = db_session.create_session()
    db_sess.add(user)
    db_sess.commit()


@app.route("/")
def index():
    if current_user.is_active:
        print(current_user.name)
        return redirect('/my_files')
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    if current_user.is_active:
        return redirect('/my_files')
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        os.mkdir(f'{PATH_TO_STORAGE}/{form.name.data}')
        login_user(user)
        return redirect("/my_files")
    return render_template('register.html', title='Регистрация', form=form)



@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_active:
        return redirect('/my_files')
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/my_files")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route("/delete/<path:subpath>", methods=['GET', 'POST'])
def delete(**path):
    path = path['subpath']
    pth = f'{PATH_TO_STORAGE}/{current_user.name}/{path}'
    os.remove(pth)
    return redirect('/'.join(['/my_files'] + path.split('/')[:-1]))


@app.route("/my_files", methods=['GET', 'POST'])
@app.route("/my_files/", methods=['GET', 'POST'])
@app.route("/my_files/<path:subpath>", methods=['GET', 'POST'])
def my_files(**path):
    if not current_user.is_active:
        redirect('/login')
    if path:
        path = path['subpath']
    else:
        path = None
    print('asked ' + str(path))
    pth = f'{PATH_TO_STORAGE}/{current_user.name}'
    lnk = ['my_files']
    name = 'ваши файлы'
    back = False
    if path:
        back = True
        name += '/' + path
        pth += '/' + path
        lnk += path.split('/')
    if request.method == 'GET':
        try:
            print(os.listdir(pth))
            items = {'data': [{'name': i, 'link': f'{"/".join(lnk)}/{i}',
                               'del_link': f'{"/".join(lnk)}/{i}'.replace('my_files', 'delete')} for i in
                              sorted(list(os.listdir(pth)), key=lambda x: x.count('.'))], 'name': name, 'back': back}
            return render_template('my_files.html', files=items)

        except Exception as e:
            print(e.args[0])
            if e.args[0] == 2:
                print('wrong_directory')
            elif e.args[0] == 20:
                return send_file(pth, as_attachment=True)
            else:
                print(e)
            return {'error': e}
    elif request.method == 'POST':
        if request.form:
            os.mkdir(f'{pth}/{request.form["folder_name"]}')
            items = {'data': [{'name': i, 'link': f'{"/".join(lnk)}/{i}',
                               'del_link': f'{"/".join(lnk)}/{i}'.replace('my_files', 'delete')} for i in
                              sorted(list(os.listdir(pth)), key=lambda x: x.count('.'))], 'name': name, 'back': back}
            return render_template('my_files.html', files=items)
        else:
            try:
                file = request.files['file']
                print(f'{pth}/{file.filename}')
                with open(f'{pth}/{file.filename}', mode='wb+') as fl:
                    fl.write(file.read())
                items = {'data': [{'name': i, 'link': f'{"/".join(lnk)}/{i}',
                                   'del_link': f'{"/".join(lnk)}/{i}'.replace('my_files', 'delete')} for i in
                                  sorted(list(os.listdir(pth)), key=lambda x: x.count('.'))], 'name': name, 'back': back}
                return render_template('my_files.html', files=items)
            except Exception as e:
                print(e)





@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")



@app.errorhandler(400)
def bad_request(_):
    return make_response(jsonify({'error': 'Bad Request'}), 400)

if __name__ == '__main__':
    main()