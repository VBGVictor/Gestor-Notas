# 🏥 GestorNotas

Sistema básico para **gestão de geração de notas de prestação de serviços** voltado para profissionais da área da **saúde**.

---

## 📌 Objetivo

Este projeto tem como objetivo fornecer um sistema web simples e funcional para **registrar usuários**, **gerar notas**, e **organizar os dados** relacionados às atividades prestadas por profissionais da saúde (como psicólogos, fisioterapeutas, terapeutas, etc.).

---

## 🧩 Funcionalidades

- ✅ Cadastro e login de usuários (autenticação com Firebase)
- ✅ Dashboard protegido para usuários autenticados
- ✅ Upload e leitura de planilhas Excel com dados das sessões
- ✅ Interface interativa com HTML + CSS (pronto para integração com frontend moderno)
- 🚧 Em desenvolvimento: geração automática de notas, relatórios mensais e exportações

---

## 🛠️ Tecnologias Utilizadas

### Backend:
- [Flask](https://flask.palletsprojects.com/) (Python)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin)
- [Firestore](https://firebase.google.com/docs/firestore) como banco de dados
- [Gunicorn](https://gunicorn.org/) para deployment em produção

### Frontend:
- HTML5 + CSS3 (em estrutura básica)
- Bootstrap (pronto para ser integrado)
- Template rendering com Jinja2 (Flask)

---

## 🚀 Como Executar Localmente

1. **Clone o projeto:**
   ```bash
   git clone https://github.com/seu-usuario/gestor_notas.git
   cd gestor_notas


2. **Clone um ambiente virtual e instale as dependencias:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt


3. **Configure as variáveis de ambiente**
   
4. **Rode o servidor Flak**


