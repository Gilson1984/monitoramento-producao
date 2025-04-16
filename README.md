# monitoramento-producao
istema de monitoramento de produção com interface gráfica em Python, utilizando PostgreSQL como banco de dados.

## Funcionalidades

- Monitoramento em tempo real da produção
- Registro de paradas de produção
- Gráficos de análise de paradas
- Cálculo de probabilidade de atingir metas
- Estatísticas detalhadas de produção

## Requisitos

- Python 3.8 ou superior
- PostgreSQL
- Bibliotecas Python:
  - tkinter
  - psycopg2
  - matplotlib

## Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITORIO]
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure o banco de dados PostgreSQL:
   - Crie um banco de dados chamado 'producao'
   - Atualize as credenciais no arquivo principal

4. Execute o programa:
```bash
python "Monitoramento de Produção - Versão Pyt.py"
```

## Configuração do Banco de Dados

1. Crie o banco de dados:
```sql
CREATE DATABASE producao
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Portuguese_Brazil.1252'
    LC_CTYPE = 'Portuguese_Brazil.1252'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;
```

2. A tabela será criada automaticamente na primeira execução do programa.

## Estrutura do Projeto

- `Monitoramento de Produção - Versão Pyt.py`: Arquivo principal do programa
- `create_database.sql`: Script SQL para criar o banco de dados
- `requirements.txt`: Lista de dependências do projeto

## Contribuição

Sinta-se à vontade para contribuir com o projeto. Abra uma issue ou envie um pull request.

## Licença

Este projeto está sob a licença MIT. 
