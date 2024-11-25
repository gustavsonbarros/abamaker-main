import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import send_from_directory
from flask import Response
import csv

# Configuração da aplicação
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cimas_maker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Inicializando o banco de dados
db = SQLAlchemy(app)

# Modelos
class Projeto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    data_submissao = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(50), nullable=False)

class Instituicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), nullable=False)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(50), nullable=False, default="aluno")

# Função para criar tabelas e dados iniciais
def criar_tabelas_e_inserir_dados():
    db.create_all()  # Criação das tabelas
    # Criar usuário admin
    if not Usuario.query.filter_by(email='admin@example.com').first():
        admin = Usuario(
            nome="Administrador",
            email="admin@example.com",
            senha=generate_password_hash("admin123"),
            tipo="admin"
        )
        db.session.add(admin)
    
    # Criar usuário aluno
    if not Usuario.query.filter_by(email='aluno@example.com').first():
        aluno = Usuario(
            nome="Aluno",
            email="aluno@example.com",
            senha=generate_password_hash("aluno123"),
            tipo="aluno"
        )
        db.session.add(aluno)

    # Criar projetos
    if not Projeto.query.first():
        projetos = [
            Projeto(nome="Projeto de Pesquisa A", data_submissao="12/11/2024", status="Pendente"),
            Projeto(nome="Projeto de Pesquisa B", data_submissao="11/11/2024", status="Aprovado")
        ]
        db.session.add_all(projetos)

    # Criar instituições
    if not Instituicao.query.first():
        instituicoes = [
            Instituicao(nome="Instituição X", status="Aprovada"),
            Instituicao(nome="Instituição Y", status="Suspensa")
        ]
        db.session.add_all(instituicoes)

    db.session.commit()

@app.route('/editar_perfil')
def editar_perfil():
    return render_template('editar_perfil.html')

# Rota para a página de recuperação de senha
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # Aqui vai a lógica para enviar o e-mail de recuperação de senha
        return redirect(url_for('login'))
    return render_template('forgot_password.html')


# Rotas e funcionalidades
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_panel')
def admin_panel():
    if 'user_id' not in session or session.get('tipo') != 'admin':
        flash("Acesso negado. Faça login como admin.", "danger")
        return redirect(url_for('login'))
    
    instituicoes = Instituicao.query.all()  # Certifique-se de que há dados no banco
    projetos = Projeto.query.all()

    # Resumo de projetos
    projetos_pendentes = Projeto.query.filter_by(status='Pendente').count()
    projetos_aprovados = Projeto.query.filter_by(status='Aprovado').count()
    projetos_rejeitados = Projeto.query.filter_by(status='Rejeitado').count()

    return render_template(
        'admin_panel.html',
        instituicoes=instituicoes,
        projetos=projetos,
        projetos_pendentes=projetos_pendentes,
        projetos_aprovados=projetos_aprovados,
        projetos_rejeitados=projetos_rejeitados
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar-senha']

        # Verificar se as senhas coincidem
        if senha != confirmar_senha:
            flash("As senhas não coincidem. Tente novamente.", "danger")
            return redirect(url_for('register'))

        # Verificar se o email já está cadastrado
        if Usuario.query.filter_by(email=email).first():
            flash("Email já cadastrado. Tente outro.", "danger")
            return redirect(url_for('register'))

        # Criptografar a senha antes de salvar
        senha_hash = generate_password_hash(senha)

        usuario = Usuario(nome=nome, email=email, senha=senha_hash, tipo="aluno")
        db.session.add(usuario)
        db.session.commit()

        flash("Cadastro realizado com sucesso!", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/adicionar_instituicao', methods=['GET', 'POST'])
def adicionar_instituicao():
    if 'user_id' not in session or session.get('tipo') != 'admin':
        flash("Acesso negado. Faça login como admin.", "danger")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        status = request.form['status']

        if not nome or not status:
            flash("Todos os campos são obrigatórios!", "danger")
            return redirect(url_for('adicionar_instituicao'))
        
        nova_instituicao = Instituicao(nome=nome, status=status)
        db.session.add(nova_instituicao)
        db.session.commit()
        flash("Instituição cadastrada com sucesso!", "success")
        return redirect(url_for('admin_panel'))
    
    return render_template('adicionar_instituicao.html')


@app.route('/adicionar_projeto', methods=['GET', 'POST'])
def adicionar_projeto():
    if 'user_id' not in session or session.get('tipo') != 'admin':
        flash("Acesso negado. Faça login como admin.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        data_submissao = request.form['data_submissao']
        status = request.form['status']

        # Validação dos campos
        if not nome or not data_submissao or not status:
            flash("Todos os campos são obrigatórios!", "danger")
            return redirect(url_for('adicionar_projeto'))

        # Criar novo projeto
        novo_projeto = Projeto(nome=nome, data_submissao=data_submissao, status=status)
        db.session.add(novo_projeto)
        db.session.commit()

        flash("Projeto adicionado com sucesso!", "success")
        return redirect(url_for('projetos'))

    return render_template('adicionar_projeto.html')


@app.route('/aprovar_projeto/<int:id>', methods=['POST'])
def aprovar_projeto(id):
    projeto = Projeto.query.get_or_404(id)
    if projeto.status == 'Pendente':
        projeto.status = 'Aprovado'
        db.session.commit()
        return {'success': True}
    return {'success': False}, 400


@app.route('/rejeitar_projeto/<int:id>', methods=['POST'])
def rejeitar_projeto(id):
    projeto = Projeto.query.get_or_404(id)
    if projeto.status == 'Pendente':
        projeto.status = 'Rejeitado'
        db.session.commit()
        return {'success': True}
    return {'success': False}, 400


@app.route('/suspender_instituicao/<int:id>', methods=['POST'])
def suspender_instituicao(id):
    instituicao = Instituicao.query.get_or_404(id)
    if instituicao.status != "Suspensa":
        instituicao.status = "Suspensa"
        db.session.commit()
        return {'success': True, 'status': 'Suspensa', 'nome': instituicao.nome}, 200
    return {'success': False, 'message': f"A instituição '{instituicao.nome}' já está suspensa."}, 400


@app.route('/reativar_instituicao/<int:id>', methods=['POST'])
def reativar_instituicao(id):
    instituicao = Instituicao.query.get_or_404(id)
    if instituicao.status != "Aprovada":
        instituicao.status = "Aprovada"
        db.session.commit()
        return {'success': True, 'status': 'Aprovada', 'nome': instituicao.nome}, 200
    return {'success': False, 'message': f"A instituição '{instituicao.nome}' já está aprovada."}, 400


@app.route('/excluir_instituicao/<int:id>', methods=['DELETE'])
def excluir_instituicao(id):
    instituicao = Instituicao.query.get_or_404(id)
    db.session.delete(instituicao)
    db.session.commit()
    return {'success': True, 'nome': instituicao.nome}, 200

@app.route('/gerar_relatorio_csv', methods=['GET'])
def gerar_relatorio_csv():
    # Exemplo de dados a serem exportados para CSV
    instituicoes = get_instituicoes()  # Suponha que você tenha uma função que retorna as instituições
    
    # Cabeçalhos do CSV
    csv_file = "instituicoes.csv"
    headers = ['ID', 'Nome', 'Status']
    
    # Resposta de CSV
    def generate():
        yield ','.join(headers) + '\n'
        for instituicao in instituicoes:
            yield f"{instituicao['id']},{instituicao['nome']},{instituicao['status']}\n"
    
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename={csv_file}"})




# Função auxiliar para verificar tipos de arquivo permitidos
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


# Lista para armazenar informações de arquivos (substitua por banco de dados no futuro)
arquivos = []

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('aluno'))

    file = request.files['file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('aluno'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Armazenar informações do arquivo
        arquivos.append({
            'nome': filename,
            'data': datetime.now().strftime('%d/%m/%Y %H:%M')
        })

        flash('Arquivo enviado com sucesso!', 'success')
        return redirect(url_for('aluno'))

    flash('Tipo de arquivo não permitido.', 'danger')
    return redirect(url_for('aluno'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.senha, senha):
            session['user_id'] = usuario.id
            session['tipo'] = usuario.tipo
            
            # Mensagem de boas-vindas personalizada
            flash(f"Bem-vindo(a) {usuario.nome}!", "success")
            
            # Redirecionamento baseado no tipo de usuário
            if usuario.tipo == 'admin':
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('aluno'))
        flash("Credenciais inválidas.", "danger")
    return render_template('login.html')

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session or session.get('tipo') != 'aluno':
        flash("Acesso negado. Faça login como aluno.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    aluno = Usuario.query.get_or_404(user_id)
    
    # Atualiza nome e email
    aluno.nome = request.form['nome']
    aluno.email = request.form['email']

    # Verifica se a foto foi enviada
    if 'foto_perfil' in request.files:
        file = request.files['foto_perfil']
        if file and allowed_file(file.filename):
            # Garante que o nome do arquivo seja seguro
            filename = secure_filename(file.filename)
            
            # Salva o arquivo no diretório de uploads
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Atualiza o campo foto_perfil no banco de dados
            aluno.foto_perfil = filename
    
    db.session.commit()
    flash("Perfil atualizado com sucesso!", "success")
    return redirect(url_for('aluno'))


@app.route('/logout')
def logout():
    session.clear()
    flash("Você foi desconectado com sucesso.", "info")
    return redirect(url_for('login'))



@app.route('/alunohtml', methods=['GET', 'POST'])
def alunohtml():
    if request.method == 'POST':
        # Verificar se o arquivo foi enviado
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Salvar o arquivo com nome seguro
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Adicionar informações do arquivo à lista
            data_envio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            arquivos.append({'nome': filename, 'data': data_envio})
            return redirect(url_for('alunohtml'))

    return render_template('alunohtml.html', arquivos=arquivos)

@app.route('/projetos', methods=['GET'])
def projetos():
    projetos = Projeto.query.all()  # Obter todos os projetos do banco de dados
    return render_template('projetos.html', projetos=projetos)



@app.route('/aluno')
def aluno():
    if 'user_id' not in session or session.get('tipo') != 'aluno':
        flash("Acesso negado. Faça login como aluno.", "danger")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    aluno = Usuario.query.get_or_404(user_id)
    
    # Contar projetos por status
    projetos_pendentes = Projeto.query.filter_by(status='Pendente').count()
    projetos_aprovados = Projeto.query.filter_by(status='Aprovado').count()
    projetos_rejeitados = Projeto.query.filter_by(status='Rejeitado').count()
    
    # Renderizar a lista de arquivos e resumo dos projetos no template
    return render_template(
        'aluno.html',
        aluno=aluno,
        arquivos=arquivos,
        projetos_pendentes=projetos_pendentes,
        projetos_aprovados=projetos_aprovados,
        projetos_rejeitados=projetos_rejeitados
    )




@app.route('/projeto/<int:id>', methods=['GET'])
def detalhes_projeto(id):
    projeto = Projeto.query.get_or_404(id)
    return render_template('detalhes_projeto.html', projeto=projeto)

# API para retorno de detalhes do projeto em formato JSON
@app.route('/api/projeto/<int:id>', methods=['GET'])
def api_detalhes_projeto(id):
    projeto = Projeto.query.get_or_404(id)
    return {
        'id': projeto.id,
        'nome': projeto.nome,
        'data_submissao': projeto.data_submissao,
        'status': projeto.status
    }



@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/delete/<filename>', methods=['POST'])
def delete(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        
        global arquivos
        arquivos = [arquivo for arquivo in arquivos if arquivo['nome'] != filename]
        flash(f"Arquivo '{filename}' excluído com sucesso.", 'success')
    else:
        flash(f"Arquivo '{filename}' não encontrado.", 'danger')
    return redirect(url_for('aluno'))


@app.route('/api/projetos/stats', methods=['GET'])
def projetos_stats():
    if 'user_id' not in session or session.get('tipo') != 'aluno':
        return {'error': 'Unauthorized'}, 401

    stats = {
        'Concluídos': Projeto.query.filter_by(status='Concluído').count(),
        'Em andamento': Projeto.query.filter_by(status='Em andamento').count(),
        'Aguardando revisão': Projeto.query.filter_by(status='Aguardando revisão').count()
    }
    return stats

# Inicializar tabelas
with app.app_context():
    criar_tabelas_e_inserir_dados()

if __name__ == '__main__':
    # Verificar e criar diretório de uploads
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)