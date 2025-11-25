import tkinter as tk
from tkinter import ttk, messagebox
import os
import multiprocessing
import time
import threading
import queue 
try:
    from modules import models, data_access, services, utils
except ImportError as e:
    print(f"Erro: Não foi possível importar os módulos da arquitetura.")
    print(f"Verificar se os módulos existem ou se o caminho está correto.")
    print(f"Erro: {e}")
    exit()

# Tamanho do chunk para usar durante o mergesort
CHUNK_RECORDS_PARA_MERGE = 10_000

# Número de registros a gerar se os arquivos não existirem
NUM_REGS_FUNCIONARIOS = 100_000  
NUM_REGS_PACIENTES = 100_000    
NUM_REGS_VACINAS = 100_000  

# O sistema realiza as funções de reordenação após alteração em segundo plano, de forma assíncrona, usando uma nova thread

# FUNÇÃO DE SETUP

def _setup_database_files():
    
    # Verifica gera e ordena os arquivos necessários na inicialização.
    
    print("--- INICIANDO VERIFICAÇÃO DOS ARQUIVOS DE DADOS ---")

    # Garante que o diretório "files" exista
    try:
        os.makedirs("files", exist_ok=True)
        print("Diretório 'files/' verificado/criado.")
    except OSError as e:
        print(f"ERRO CRÍTICO ao criar o diretório 'files': {e}")
        messagebox.showerror("Erro de Inicialização",
                             f"Não foi possível criar o diretório 'files'.\nErro: {e}\n\nA aplicação será encerrada.")
        exit()
    
    # Define os arquivos que o sistema precisa gerenciar
    files_to_manage = [
        (models.FILE_FUNCIONARIOS, models.Funcionario, models.RECORD_SIZE_FUNC, NUM_REGS_FUNCIONARIOS, utils.gera_arquivo_FUNCIONARIOS_paralelo),
        (models.FILE_PACIENTES, models.Paciente, models.RECORD_SIZE_PAC, NUM_REGS_PACIENTES, utils.gera_arquivo_PACIENTES_paralelo),
        (models.FILE_VACINAS, models.Vacina, models.RECORD_SIZE_VAC, NUM_REGS_VACINAS, utils.gera_arquivo_VACINAS_paralelo),
        (models.FILE_APLICACOES, models.AplicacaoVacina, models.RECORD_SIZE_APLIC, 0, None) # Arquivo de relacionamento, começa vazio
    ]

    for filename, struct_class, rec_size, num_to_gen, gen_func in files_to_manage:
        print(f"\nVerificando '{filename}'...")
        try:
            # Arquivo não existe ?
            if not os.path.exists(filename):
                if num_to_gen > 0 and gen_func is not None:
                    print(f"Arquivo não encontrado. Gerando {num_to_gen:,} novos registros...")
                    gen_func(filename, num_to_gen, rec_size)
                    # O arquivo gerado já vem ordenado por cod
                else:
                    print(f"Arquivo não encontrado. Criando arquivo vazio.")
                    open(filename, 'wb').close() # Cria arquivo vazio
            
            # Arquivo existe! Está ordenado?
            else:
                print("Arquivo encontrado. Verificando ordenação...")
                if not utils.verifica_ordenacao(filename, struct_class, rec_size):
                    print(f"Arquivo '{filename}' está desordenado. Iniciando mergesort...")
                    
                    utils._log_operacao(f"Inicialização: Detectado arquivo desordenado '{filename}'. Iniciando mergesort.", "ALERTA")
                    
                    utils.mergesort_file(filename, struct_class, rec_size, CHUNK_RECORDS_PARA_MERGE)
                    
                    utils._log_operacao(f"Inicialização: Arquivo '{filename}' reordenado com sucesso.", "INFO")
                else:
                    print(f"Arquivo '{filename}' já está ordenado. (OK)")
        
        except Exception as e:
            print(f"Erro durante o setup do arquivo '{filename}': {e}")
            messagebox.showerror("Erro de Inicialização", 
                                 f"Falha ao verificar/gerar o arquivo '{filename}'.\nErro: {e}\n\nA aplicação será encerrada.")
            exit()

    print("\n--- Verificação concluída ---")

class App(tk.Tk):
    # Classe principal da aplicação GUI

    def __init__(self):
        super().__init__()
        
        self.title("Sistema de Vacinação - (Arquivos Binários)")
        self.geometry("700x600")
        self.configure(bg="#f0f0f0")

        # Fila para comunicação entre a thread de sort e a interface
        self.sort_queue = queue.Queue()

        # Container Principal
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        self.status_frame = ttk.Frame(main_frame, relief="sunken", padding=5)
        self.status_label = ttk.Label(self.status_frame, text="Status: Pronto.", font=("Arial", 10))
        self.status_label.pack(side="left")
        self.status_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        # Canvas e Scrollbar
        self.canvas = tk.Canvas(main_frame, borderwidth=0, background="#f0f0f0")
        self.scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        
        # Container de Conteúdo rolável
        self.container = tk.Frame(self.canvas, background="#f0f0f0")

        # Configurações de rolagem
        self.scrollable_window = self.canvas.create_window((0, 0), window=self.container, anchor="nw")

        def configure_scroll_region(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def configure_window_width(event):
            self.canvas.itemconfig(self.scrollable_window, width=event.width)

        self.container.bind("<Configure>", configure_scroll_region)
        self.canvas.bind("<Configure>", configure_window_width)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.bind_all("<MouseWheel>", self._on_mousewheel)

        # Dicionário de frames
        self.frames = {}
        
        classes_de_frames = [FrameHome, FrameLista, FrameAplicacao, FrameGerarCartao, FrameManutencao]

        for F in classes_de_frames: 
            frame_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[frame_name] = frame
            frame.grid(row=0, column=0, sticky="nsew") 

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.mostrar_frame("FrameHome")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def mostrar_frame(self, frame_name: str):
        # Traz um frame para a frente
        frame = self.frames[frame_name]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()

    # Funções de Controle da GUI

    def _iniciar_reordenacao_automatica(self):
        """Inicia a operação de ordenação em uma thread separada."""
        print("GUI: Iniciando reordenação automática assíncrona...")
        
        # Bloqueia a GUI
        self._bloquear_gui(True)
        self.status_label.config(text="Status: REORDENANDO... Por favor, aguarde (pode levar minutos).")
        
        # Cria e inicia a thread para o sorting
        self.sort_thread = threading.Thread(
            target=self._worker_sort_e_index,
            daemon=True # Mata a thread se a janela for fechada
        )
        self.sort_thread.start()
        
        # Inicia um listener para saber quando a thread terminou
        self._verificar_thread_sort()

    def _worker_sort_e_index(self):
        # Faz o Mergesort e reconstrói o índice

        try:
            print("THREAD-SORT: Iniciando mergesort de Aplicações...")
            utils._log_operacao(f"Auto-Sort: Mergesort automático iniciado para '{models.FILE_APLICACOES}'.", "INFO")
            
            utils.mergesort_file(
                models.FILE_APLICACOES, 
                models.AplicacaoVacina, 
                models.RECORD_SIZE_APLIC, 
                CHUNK_RECORDS_PARA_MERGE
            )
            print("THREAD-SORT: Mergesort concluído. Reconstruindo índice de pacientes...")
            utils._log_operacao(f"Auto-Sort: Mergesort de '{models.FILE_APLICACOES}' concluído.", "INFO")
            
            # Reconstrói o índice que foi invalidado
            utils.reconstruir_indice_paciente()
            
            print("THREAD-SORT: Índice reconstruído.")
            utils._log_operacao(f"Auto-Sort: Índice '{models.FILE_IDX_PACIENTE_APLIC}' reconstruído.", "INFO")
            
            # Envia mensagem de sucesso para a GUI
            self.sort_queue.put("SUCESSO")
            
        except Exception as e:
            print(f"THREAD-SORT: ERRO CRÍTICO durante a reordenação: {e}")
            utils._log_operacao(f"Auto-Sort: FALHA CRÍTICA. Erro: {e}", "CRÍTICO")
            self.sort_queue.put(f"ERRO: {e}")

    def _verificar_thread_sort(self):
        # Verifica a fila por mensagens da thread
        try:
            # Tenta pegar uma mensagem da fila sem bloquear
            mensagem = self.sort_queue.get(block=False)
            
            if mensagem == "SUCESSO":
                self._bloquear_gui(False) # Desbloqueia a GUI
                self.status_label.config(text="Status: Pronto. Arquivos reordenados.")
                messagebox.showinfo("Manutenção Concluída", 
                                    "Os arquivos foram reordenados com sucesso em segundo plano.")
            else:
                # É uma mensagem de erro
                self._bloquear_gui(False)
                self.status_label.config(text="Status: ERRO NA ORDENAÇÃO. Verifique os logs.")
                messagebox.showerror("Erro na Manutenção", 
                                     f"Ocorreu um erro ao reordenar os arquivos:\n{mensagem}")
        
        except queue.Empty:
            # Se fila vazia thread ainda está rodando, verifica de novo em 100ms.
            self.after(100, self._verificar_thread_sort)

    def _bloquear_gui(self, bloquear: bool):
        # Habilita ou desabilita widgets interativos
        estado = "disabled" if bloquear else "normal"
        # Itera por todos os widgets em todos os frames
        for frame in self.frames.values():
            for widget in frame.winfo_children():
                if isinstance(widget, (ttk.Button, ttk.Entry)):
                    widget.config(state=estado)
                if isinstance(widget, ttk.Frame):
                    for sub_widget in widget.winfo_children():
                        if isinstance(sub_widget, (ttk.Button, ttk.Entry)):
                            sub_widget.config(state=estado)

# PÁGINA INICIAL

class FrameHome(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        lbl_title = ttk.Label(self, text="Sistema de Vacinação", font=("Arial", 22, "bold"))
        lbl_title.pack(pady=30)
        
        # Botões Principais
        frame_botoes = ttk.Frame(self)
        frame_botoes.pack(fill="x", padx=50)

        self.btn_pac = ttk.Button(frame_botoes, text="📂 Listar Pacientes",
            command=lambda: self.controller.frames["FrameLista"].preparar_lista(
                "Lista de Pacientes", models.FILE_PACIENTES, models.RECORD_SIZE_PAC, models.Paciente
            ))
        self.btn_pac.pack(fill="x", pady=5)

        self.btn_vac = ttk.Button(frame_botoes, text="📂 Listar Vacinas",
            command=lambda: self.controller.frames["FrameLista"].preparar_lista(
                "Lista de Vacinas", models.FILE_VACINAS, models.RECORD_SIZE_VAC, models.Vacina
            ))
        self.btn_vac.pack(fill="x", pady=5)

        self.btn_func = ttk.Button(frame_botoes, text="📂 Listar Funcionários",
            command=lambda: self.controller.frames["FrameLista"].preparar_lista(
                "Lista de Funcionários", models.FILE_FUNCIONARIOS, models.RECORD_SIZE_FUNC, models.Funcionario
            ))
        self.btn_func.pack(fill="x", pady=5)
        
        ttk.Separator(frame_botoes, orient='horizontal').pack(fill='x', pady=15)

        self.btn_aplicar = ttk.Button(frame_botoes, text="💉 Registrar Nova Aplicação",
                                 command=lambda: controller.mostrar_frame("FrameAplicacao"))
        self.btn_aplicar.pack(fill="x", pady=5)

        self.btn_cartao = ttk.Button(frame_botoes, text="📄 Gerar Cartão (PDF)",
                                command=lambda: controller.mostrar_frame("FrameGerarCartao"))
        self.btn_cartao.pack(fill="x", pady=5)
        
        ttk.Separator(frame_botoes, orient='horizontal').pack(fill='x', pady=15)
        
        self.btn_manut = ttk.Button(frame_botoes, text="🛠️ Manutenção e Debug",
                                command=lambda: controller.mostrar_frame("FrameManutencao"))
        self.btn_manut.pack(fill="x", pady=5)


    def _gerar_random(self, controller):
        resposta = messagebox.askyesno("Confirmar", "Isso irá gerar 5.000 registros aleatórios e desordenar o arquivo.\nDeseja continuar?")
        if resposta:
            sucesso, msg = utils.gerar_lote_aplicacoes_aleatorias(5000)
            if sucesso:
                messagebox.showinfo("Sucesso", f"{msg}\n\nO sistema irá iniciar a reordenação agora.")
                # Reordenação automática
                services._invalidar_indice_paciente() # Garante que o indice fique inválido
                controller._iniciar_reordenacao_automatica()
            else:
                messagebox.showerror("Erro", msg)
        
        # Botões de Ação
        separator = ttk.Separator(self, orient='horizontal')
        separator.pack(fill='x', pady=15)

        # self.btn_aplicar = ttk.Button(self, text="Registrar Nova Aplicação",
        #                          command=lambda: controller.mostrar_frame("FrameAplicacao"))
        # self.btn_aplicar.pack(fill="x", pady=5)

# PÁGINA DE DEBUG

class FrameManutencao(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        lbl_title = ttk.Label(self, text="Manutenção e Debug", font=("Arial", 18, "bold"))
        lbl_title.pack(pady=20)
        
        # Área de Geração de Dados
        group_gen = ttk.LabelFrame(self, text=" Gerador de Dados de Teste ", padding=15)
        group_gen.pack(padx=20, pady=10, fill="x")
        
        ttk.Label(group_gen, text="Gerar aplicações aleatórias.", font=("Arial", 10, "italic")).pack(pady=(0,10))

        frame_form = ttk.Frame(group_gen)
        frame_form.pack()

        # Input ID Paciente
        ttk.Label(frame_form, text="ID Paciente Alvo (Opcional):").grid(row=0, column=0, sticky="e", padx=5)
        self.entry_pac_id = ttk.Entry(frame_form, width=10)
        self.entry_pac_id.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(frame_form, text="(Deixe vazio para aleatório)").grid(row=0, column=2, sticky="w", padx=5)

        # Input Quantidade
        ttk.Label(frame_form, text="Quantidade:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_qtd = ttk.Entry(frame_form, width=10)
        self.entry_qtd.insert(0, "50") # Default
        self.entry_qtd.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.btn_gerar = ttk.Button(group_gen, text="Gerar Dados", command=self._gerar_dados)
        self.btn_gerar.pack(pady=10)
        
        # Área de Reordenação Manual
        group_sort = ttk.LabelFrame(self, text=" Ferramentas de Arquivo ", padding=15)
        group_sort.pack(padx=20, pady=10, fill="x")
        
        self.btn_sort = ttk.Button(group_sort, text="Forçar Reordenação e Indexação Agora", 
                                   command=self._forcar_sort)
        self.btn_sort.pack(fill="x")

        # Botão Voltar
        self.btn_voltar = ttk.Button(self, text="Voltar ao Menu",
                                command=lambda: controller.mostrar_frame("FrameHome"))
        self.btn_voltar.pack(pady=20)

    def _gerar_dados(self):
        qtd_str = self.entry_qtd.get()
        pac_id_str = self.entry_pac_id.get()
        
        if not qtd_str.isdigit():
            messagebox.showerror("Erro", "Quantidade inválida.")
            return
            
        qtd = int(qtd_str)
        pac_id = int(pac_id_str) if pac_id_str.isdigit() else None
        
        msg_confirm = f"Gerar {qtd} registros"
        if pac_id:
            msg_confirm += f" APENAS para o Paciente {pac_id}?"
        else:
            msg_confirm += " para pacientes aleatórios?"
            
        if messagebox.askyesno("Confirmar", f"{msg_confirm}\nIsso deixará o arquivo desordenado."):
            sucesso, msg = utils.gerar_lote_aplicacoes_aleatorias(qtd, pac_id)
            if sucesso:
                messagebox.showinfo("Sucesso", msg + "\nIniciando reordenação...")
                # Invalida indice e chama reordenação
                services._invalidar_indice_paciente()
                self.controller._iniciar_reordenacao_automatica()
            else:
                messagebox.showerror("Erro", msg)

    def _forcar_sort(self):
        if messagebox.askyesno("Confirmar", "Deseja rodar o processo de Mergesort e Indexação manualmente?"):
             services._invalidar_indice_paciente()
             self.controller._iniciar_reordenacao_automatica()
        
# PÁGINA DE LISTAGEM

class FrameLista(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.lbl_list_title = ttk.Label(self, text="", font=("Arial", 18, "bold"))
        self.lbl_list_title.pack(pady=10)
        
        list_container = ttk.Frame(self)
        list_container.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_container, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.txt_lista = tk.Text(
            list_container, wrap="none", font=("Courier New", 10), 
            yscrollcommand=scrollbar.set, state="disabled"
        )
        self.txt_lista.pack(fill="both", expand=True, side="left")
        scrollbar.config(command=self.txt_lista.yview)

        self.btn_voltar = ttk.Button(self, text="Voltar ao Menu",
                                command=lambda: controller.mostrar_frame("FrameHome"))
        self.btn_voltar.pack(pady=10)

        self.loader_args = None # Limpa os args

    def preparar_lista(self, title, filename, record_size, structure_class):
        # Guarda os argumentos para carregar a lista e mostra o frame
        self.lbl_list_title.config(text=title)
        self.loader_args = (filename, record_size, structure_class)
        self.controller.mostrar_frame("FrameLista")

    def on_show(self):
        # Chamado quando o frame é exibido
        if self.loader_args:
            filename, record_size, structure_class = self.loader_args
            
            self.txt_lista.config(state="normal")
            self.txt_lista.delete("1.0", tk.END)
            
            print(f"GUI: Carregando dados de '{filename}'...")
            registros = data_access.ler_sequencial(filename, record_size, structure_class)
            print(f"GUI: Encontrados {len(registros)} registros.")

            if not registros:
                self.txt_lista.insert(tk.END, f"Nenhum registro encontrado em '{filename}'.")
            else:
                for r in registros:
                    self.txt_lista.insert(tk.END, str(r) + "\n\n") 
            
            self.txt_lista.config(state="disabled")
            self.loader_args = None # Limpa os args

# APLICAÇÃO DE VACINA

class FrameAplicacao(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        lbl_title = ttk.Label(self, text="Registrar Nova Aplicação", font=("Arial", 18, "bold"))
        lbl_title.pack(pady=20)
        
        form_frame = ttk.Frame(self)
        form_frame.pack(padx=20)
        
        ttk.Label(form_frame, text="ID do Paciente:", font=("Arial", 11)).grid(row=0, column=0, sticky="w", pady=5)
        ttk.Label(form_frame, text="ID da Vacina:", font=("Arial", 11)).grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(form_frame, text="ID do Funcionário:", font=("Arial", 11)).grid(row=2, column=0, sticky="w", pady=5)
        ttk.Label(form_frame, text="Data (dd/mm/aaaa):", font=("Arial", 11)).grid(row=3, column=0, sticky="w", pady=5)
        
        self.entry_pac_id = ttk.Entry(form_frame, font=("Arial", 11))
        self.entry_vac_id = ttk.Entry(form_frame, font=("Arial", 11))
        self.entry_func_id = ttk.Entry(form_frame, font=("Arial", 11))
        self.entry_data = ttk.Entry(form_frame, font=("Arial", 11))
        
        self.entry_pac_id.grid(row=0, column=1, pady=5, padx=10)
        self.entry_vac_id.grid(row=1, column=1, pady=5, padx=10)
        self.entry_func_id.grid(row=2, column=1, pady=5, padx=10)
        self.entry_data.grid(row=3, column=1, pady=5, padx=10)
        
        action_frame = ttk.Frame(self)
        action_frame.pack(pady=20)
        
        self.btn_salvar = ttk.Button(action_frame, text="Salvar Registro", command=self._salvar_aplicacao)
        self.btn_salvar.pack(side="left", padx=10)
        
        self.btn_voltar = ttk.Button(action_frame, text="Voltar",
                                command=lambda: controller.mostrar_frame("FrameHome"))
        self.btn_voltar.pack(side="left", padx=10)
        
    def _salvar_aplicacao(self):
        # Pega os dados salva e dispara reordenação automática
        try:
            pac_id = int(self.entry_pac_id.get())
            vac_id = int(self.entry_vac_id.get())
            func_id = int(self.entry_func_id.get())
            data = self.entry_data.get()

            if not data:
                messagebox.showerror("Erro", "A data não pode estar vazia.")
                return

            # Salva o registro
            sucesso, mensagem = services.registrar_aplicacao_sem_ordenar(
                pac_id, vac_id, func_id, data
            )
            
            if sucesso:
                # Limpa os campos
                self.entry_pac_id.delete(0, tk.END)
                self.entry_vac_id.delete(0, tk.END)
                self.entry_func_id.delete(0, tk.END)
                self.entry_data.delete(0, tk.END)
                
                # Inicia a reordenação
                messagebox.showinfo("Sucesso", 
                                    f"{mensagem}\n\nPor favor aguarde.\n"
                                    "A aplicação pode ficar lenta até terminar.")
                
                self.controller.mostrar_frame("FrameHome")
                self.controller._iniciar_reordenacao_automatica()
                
            else:
                messagebox.showerror("Erro na Aplicação", mensagem)
                
        except ValueError:
            messagebox.showerror("Erro de Validação", "Os IDs devem ser números inteiros.")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {e}")

# GERAR CARTÃO

class FrameGerarCartao(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        lbl_title = ttk.Label(self, text="Gerar Cartão de Vacinação (PDF)", font=("Arial", 18, "bold"))
        lbl_title.pack(pady=30)
        
        form_frame = ttk.Frame(self)
        form_frame.pack(pady=10)
        
        ttk.Label(form_frame, text="Informe o ID do Paciente:", font=("Arial", 12)).pack(side="left", padx=5)
        self.entry_id = ttk.Entry(form_frame, font=("Arial", 12), width=15)
        self.entry_id.pack(side="left", padx=5)
        
        btn_gerar = ttk.Button(self, text="Gerar PDF", command=self._gerar_pdf)
        btn_gerar.pack(pady=20, ipadx=10, ipady=5)
        
        btn_voltar = ttk.Button(self, text="Voltar ao Menu",
                                command=lambda: controller.mostrar_frame("FrameHome"))
        btn_voltar.pack(pady=5)

    def _gerar_pdf(self):
        try:
            pac_id_str = self.entry_id.get()
            if not pac_id_str.isdigit():
                messagebox.showerror("Erro", "Por favor, insira um ID numérico válido.")
                return
            
            pac_id = int(pac_id_str)
            
            # Chama o serviço
            sucesso, msg = services.gerar_cartao_paciente_pdf(pac_id)
            
            if sucesso:
                messagebox.showinfo("Sucesso", msg)
                self.entry_id.delete(0, tk.END)
            else:
                messagebox.showwarning("Atenção", msg)
                
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Falha na interface: {e}")

# PONTO DE ENTRADA

if __name__ == "__main__":
    multiprocessing.freeze_support()
    # Verifica, gera e ordena os arquivos antes de executar a interface
    _setup_database_files()
    
    # Inicia a aplicação
    app = App()
    app.mainloop()