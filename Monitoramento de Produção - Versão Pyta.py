# Monitoramento de Produção - Versão Python com Interface Gráfica (Tkinter) e Banco de Dados PostgreSQL

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import queue
import time
from typing import Optional, Dict, Any
import sys

# Configuração do Pool de Conexões PostgreSQL
class DatabaseManager:
    _instance = None
    _connection_pool = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        try:
            # Configuração do banco de dados
            db_config = {
                'dbname': 'producao',
                'user': 'postgres',
                'password': 'sua_senha',  # Altere para sua senha
                'host': 'localhost',
                'port': '5432',
                'client_encoding': 'utf-8'
            }
            
            # Testa a conexão primeiro
            test_conn = psycopg2.connect(**db_config)
            test_conn.close()
            
            # Cria o pool de conexões
            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **db_config
            )
            self._initialize_database()
        except psycopg2.OperationalError as e:
            error_msg = f"Erro ao conectar ao banco de dados:\n{e}\n\n"
            error_msg += "Por favor, verifique se:\n"
            error_msg += "1. O PostgreSQL está instalado e rodando\n"
            error_msg += "2. O banco de dados 'producao' existe\n"
            error_msg += "3. O usuário e senha estão corretos\n"
            error_msg += "4. O servidor PostgreSQL está acessível"
            messagebox.showerror("Erro de Conexão", error_msg)
            sys.exit(1)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro inesperado: {e}")
            sys.exit(1)
    
    def _initialize_database(self):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('''
                CREATE TABLE IF NOT EXISTS paradas (
                    id SERIAL PRIMARY KEY,
                    minutos INTEGER,
                    tipo TEXT,
                    motivo TEXT,
                    responsavel TEXT,
                    data TIMESTAMP
                )''')
                conn.commit()
    
    def get_connection(self):
        return self._connection_pool.getconn()
    
    def return_connection(self, conn):
        self._connection_pool.putconn(conn)
    
    def close_all(self):
        self._connection_pool.closeall()

# Constantes e Configurações
PRODUCAO_POR_MINUTO = 90
MINUTOS_TURNO = 720
PRODUCAO_ESPERADA = PRODUCAO_POR_MINUTO * MINUTOS_TURNO
UPDATE_INTERVAL = 60000  # 1 minuto em milissegundos

class ProductionMonitor:
    def __init__(self):
        self.db = DatabaseManager.get_instance()
        self.cache = {}
        self.update_queue = queue.Queue()
        self.setup_ui()
        self.start_background_updates()
    
    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("Monitoramento de Produção")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        
        # Configuração de estilo
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()
        
        # Layout principal
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill="both", expand=True)
        
        # Painel de indicadores
        self.create_indicators_panel()
        
        # Gráfico
        self.create_chart_panel()
        
        # Formulário de paradas
        self.create_stop_form()
        
        # Botões de ação
        self.create_action_buttons()
    
    def configure_styles(self):
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Value.TLabel", font=("Segoe UI", 14))
        self.style.configure("Success.TLabel", foreground="green")
        self.style.configure("Warning.TLabel", foreground="orange")
        self.style.configure("Error.TLabel", foreground="red")
    
    def create_indicators_panel(self):
        indicators_frame = ttk.LabelFrame(self.main_frame, text="Indicadores de Produção", padding=10)
        indicators_frame.pack(fill="x", pady=10)
        
        # Grid para indicadores
        for i, (label, value) in enumerate([
            ("Produção Esperada", f"{PRODUCAO_ESPERADA}"),
            ("Probabilidade de Meta", "0%"),
            ("Tempo de Paradas", "0 min"),
            ("Produção Perdida", "0")
        ]):
            ttk.Label(indicators_frame, text=label, style="Header.TLabel").grid(row=i, column=0, sticky="w", padx=5, pady=2)
            setattr(self, f"lbl_{label.lower().replace(' ', '_')}", 
                   ttk.Label(indicators_frame, text=value, style="Value.TLabel"))
            getattr(self, f"lbl_{label.lower().replace(' ', '_')}").grid(row=i, column=1, sticky="w", padx=5, pady=2)
    
    def create_chart_panel(self):
        chart_frame = ttk.LabelFrame(self.main_frame, text="Gráfico de Produção", padding=10)
        chart_frame.pack(fill="both", expand=True, pady=10)
        
        self.figure = plt.Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.update_chart()
    
    def create_stop_form(self):
        form_frame = ttk.LabelFrame(self.main_frame, text="Registrar Parada", padding=10)
        form_frame.pack(fill="x", pady=10)
        
        # Variáveis do formulário
        self.minutos_var = tk.IntVar()
        self.tipo_var = tk.StringVar(value="mecanica")
        self.motivo_var = tk.StringVar()
        self.responsavel_var = tk.StringVar(value="operador@empresa.com")
        
        # Campos do formulário
        fields = [
            ("Minutos:", self.minutos_var, ttk.Entry),
            ("Tipo:", self.tipo_var, ttk.Combobox, ["mecanica", "operacional", "outra"]),
            ("Motivo:", self.motivo_var, ttk.Entry),
            ("Responsável:", self.responsavel_var, ttk.Entry)
        ]
        
        for i, (label, var, widget_type, *args) in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            widget = widget_type(form_frame, textvariable=var, *args)
            widget.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Button(form_frame, text="Registrar Parada", command=self.registrar_parada).grid(row=len(fields), column=0, columnspan=2, pady=10)
    
    def create_action_buttons(self):
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Estatísticas", command=self.mostrar_estatisticas).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Atualizar", command=self.atualizar_indicadores).pack(side="left", padx=5)
    
    def start_background_updates(self):
        def update_worker():
            while True:
                try:
                    self.atualizar_indicadores()
                    time.sleep(UPDATE_INTERVAL / 1000)
                except Exception as e:
                    print(f"Erro no worker de atualização: {e}")
        
        thread = threading.Thread(target=update_worker, daemon=True)
        thread.start()
    
    def calcular_producao_ajustada(self) -> int:
        with self.db.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("SELECT SUM(minutos) FROM paradas")
                total_parado = c.fetchone()[0] or 0
                minutos_ativos = max(MINUTOS_TURNO - total_parado, 0)
                return minutos_ativos * PRODUCAO_POR_MINUTO
    
    def calcular_probabilidade(self) -> float:
        producao_real = self.calcular_producao_ajustada()
        return round((producao_real / PRODUCAO_ESPERADA) * 100, 2)
    
    def atualizar_indicadores(self):
        try:
            producao_real = self.calcular_producao_ajustada()
            prob = self.calcular_probabilidade()
            
            with self.db.get_connection() as conn:
                with conn.cursor() as c:
                    c.execute("SELECT SUM(minutos) FROM paradas")
                    total_paradas = c.fetchone()[0] or 0
            
            perda = PRODUCAO_ESPERADA - producao_real
            
            # Atualizar labels
            self.lbl_produção_esperada.config(text=f"{PRODUCAO_ESPERADA}")
            self.lbl_probabilidade_de_meta.config(text=f"{prob}%")
            self.lbl_tempo_de_paradas.config(text=f"{total_paradas} min")
            self.lbl_produção_perdida.config(text=f"{perda}")
            
            # Atualizar estilo baseado na probabilidade
            style = "Success.TLabel" if prob >= 90 else "Warning.TLabel" if prob >= 70 else "Error.TLabel"
            self.lbl_probabilidade_de_meta.configure(style=style)
            
            self.update_chart()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao atualizar indicadores: {e}")
    
    def update_chart(self):
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as c:
                    c.execute("""
                        SELECT data, SUM(minutos) as total_minutos 
                        FROM paradas 
                        GROUP BY data 
                        ORDER BY data
                    """)
                    data = c.fetchall()
            
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            if data:
                dates = [row[0] for row in data]
                minutes = [row[1] for row in data]
                ax.plot(dates, minutes, marker='o')
                ax.set_title('Tempo de Paradas por Dia')
                ax.set_xlabel('Data')
                ax.set_ylabel('Minutos')
                self.figure.autofmt_xdate()
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Erro ao atualizar gráfico: {e}")
    
    def registrar_parada(self):
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as c:
                    c.execute('''
                        INSERT INTO paradas (minutos, tipo, motivo, responsavel, data)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (
                        self.minutos_var.get(),
                        self.tipo_var.get(),
                        self.motivo_var.get(),
                        self.responsavel_var.get(),
                        datetime.now()
                    ))
                    conn.commit()
            
            self.atualizar_indicadores()
            messagebox.showinfo("Sucesso", "Parada registrada com sucesso!")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao registrar parada: {e}")
    
    def mostrar_estatisticas(self):
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as c:
                    c.execute("""
                        SELECT 
                            COUNT(*) as total_paradas,
                            SUM(minutos) as total_minutos,
                            tipo,
                            COUNT(*) as paradas_por_tipo
                        FROM paradas 
                        GROUP BY tipo
                    """)
                    stats = c.fetchall()
            
            message = "Estatísticas de Paradas:\n\n"
            for stat in stats:
                message += f"Tipo: {stat[2]}\n"
                message += f"Quantidade: {stat[3]}\n"
                message += f"Tempo Total: {stat[1] or 0} min\n\n"
            
            messagebox.showinfo("Estatísticas", message)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao obter estatísticas: {e}")
    
    def run(self):
        self.root.mainloop()
        self.db.close_all()

if __name__ == "__main__":
    app = ProductionMonitor()
    app.run()
