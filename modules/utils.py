import ctypes
import os
import random
import time
import heapq
import math
import multiprocessing
from .models import (
    Funcionario, Paciente, Vacina, AplicacaoVacina, IndicePacienteAplicacao,
    LOG_FILE
)
from . import models

# FUNÇÃO DE LOG 

def _log_operacao(mensagem: str, nivel: str = "INFO"):
    #y Registra uma operação no arquivo de log central (operation_log.txt)
    try:
        # 'a' = append (adiciona ao final do arquivo)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] [{nivel.upper()}] - {mensagem}\n")
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao escrever no log '{LOG_FILE}'. Erro: {e}")

# GERAÇÃO DE DADOS 

DADOS_AMOSTRA_NOME = [
    "Ana", "Carlos", "Débora", "Gustavo", "Silvia", "Bruno", "Carla", "Diego", 
    "Gabriela", "Sofia", "Genésio", "Lucas", "Anderson", "Clara", "Hellen", 
    "Maria", "Lara", "Milena", "Ricardo", "Vanessa", "Joaquim", "Beatriz",
    "Felipe", "Elisa", "Raul", "Tatiana", "Marcos", "Livia", "Sergio", "Paula",
    "Otavio", "Julia", "Roberto", "Isabela", "Caio", "Fernanda", "Tiago"
]
DADOS_AMOSTRA_VACINA = [
    "Pfizer", "Coronavac", "AstraZeneca", "Janssen", "Sputnik V", 
    "Moderna", "Gripe (Influenza)", "Febre Amarela", "BCG", "Hepatite B"
]
DADOS_AMOSTRA_ENDERECO = [] # Não utilizado por enquanto
dados_amostra_worker = []

def _inicializa_worker_gerador(amostra):
    global dados_amostra_worker
    dados_amostra_worker = amostra
    random.seed(os.getpid())

def _gera_chunk_de_FUNCIONARIOS(args):
    start_id, tamanho_chunk, record_size_bytes = args
    print(f"[Worker {os.getpid()}] Gerando chunk de {tamanho_chunk} FUNCIONARIOS (ID: {start_id})...")
    buffer = bytearray()
    
    for i in range(start_id, start_id + tamanho_chunk):
        cod = i
        nome = dados_amostra_worker[i % len(dados_amostra_worker)]
        cpf = f"{i%1000:03}.{random.randint(100, 999)}.{random.randint(100, 999)}-{i%100:02}"
        ano = random.randint(1970, 2002)
        mes = random.randint(1, 12)
        dia = random.randint(1, 28)
        data_nascimento = f"{dia:02d}/{mes:02d}/{ano}"
        salario = round(random.uniform(1500.0, 12000.0), 2)
        
        novo_funcionario = Funcionario(cod, nome, cpf, data_nascimento, salario)
        
        buffer.extend(novo_funcionario)
        
    return buffer

def _gera_chunk_de_PACIENTES(args):
    start_id, tamanho_chunk, record_size_bytes = args
    print(f"[Worker {os.getpid()}] Gerando chunk de {tamanho_chunk} PACIENTES (ID: {start_id})...")
    
    buffer = bytearray()
    
    for i in range(start_id, start_id + tamanho_chunk):
        cod = i
        nome = dados_amostra_worker[i % len(dados_amostra_worker)]
        cpf = f"{i%1000:03}.{random.randint(100, 999)}.{random.randint(100, 999)}-{i%100:02}"
        ano = random.randint(1950, 2023)
        mes = random.randint(1, 12)
        dia = random.randint(1, 28)
        data_nascimento = f"{dia:02d}/{mes:02d}/{ano}"
        
        # Simulação de endereço
        rua = f"Rua {i % 100}"
        num = 1 + (i % 50)
        bairro = f"Bairro {i % 10}"
        endereco_completo = f"{rua}, {num} - {bairro}"
        novo_paciente = Paciente(cod, nome, cpf, data_nascimento, endereco_completo)
        
        buffer.extend(novo_paciente)
        
    return buffer

def _gera_chunk_de_VACINAS(args):
    start_id, tamanho_chunk, record_size_bytes = args
    print(f"[Worker {os.getpid()}] Gerando chunk de {tamanho_chunk} VACINAS (ID: {start_id})...")
    
    buffer = bytearray()
    
    for i in range(start_id, start_id + tamanho_chunk):
        cod = i
        fabricante = dados_amostra_worker[i % len(dados_amostra_worker)]
        lote = f"LOTE-{i%1000:03d}-{random.randint(1000, 9999)}"
        ano = random.randint(2024, 2026)
        mes = random.randint(1, 12)
        dia = random.randint(1, 28)
        data_validade = f"{dia:02d}/{mes:02d}/{ano}"
        descricao_simulada = f"Descrição da vacina {fabricante}"
        nova_vacina = Vacina(cod, fabricante, lote, data_validade, descricao_simulada)
        
        buffer.extend(nova_vacina)
        
    return buffer

def _gerador_paralelo_orchestrator(filename, num_registros, record_size_bytes, worker_function, amostra_dados, chunk_por_cpu=5):
    # Função orquestradora para geração paralela de dados.
  
    print(f"Iniciando geração de arquivo '{filename}' com {num_registros:,} registros...")
    start_time = time.perf_counter()

    try:
        num_processos = multiprocessing.cpu_count()
        total_chunks = num_processos * chunk_por_cpu
        tamanho_chunk = math.ceil(num_registros / total_chunks)
        
        lista_tarefas = []
        for i in range(total_chunks):
            start_id = 1 + (i * tamanho_chunk)
            tamanho_real = min(tamanho_chunk, num_registros - start_id + 1)
            if tamanho_real <= 0:
                break
            lista_tarefas.append((start_id, tamanho_real, record_size_bytes))

        print(f"Usando {num_processos} processos para {len(lista_tarefas)} tarefas.")
        
        with open(filename, "wb") as f:
            with multiprocessing.Pool(processes=num_processos, 
                                      initializer=_inicializa_worker_gerador, 
                                      initargs=(amostra_dados,)) as pool:
                
                total_escrito = 0
                for i, chunk_de_bytes in enumerate(pool.imap(worker_function, lista_tarefas)):
                    f.write(chunk_de_bytes)
                    
                    registros_no_chunk = len(chunk_de_bytes) // record_size_bytes
                    total_escrito += registros_no_chunk
                    print(f"Progresso: {i+1}/{len(lista_tarefas)} chunks escritos... ({total_escrito:,}/{num_registros:,} registros)")

        end_time = time.perf_counter()
        print("\n--- Concluído ---")
        print(f"Arquivo '{filename}' gerado com sucesso.")
        print(f"Tempo total: {end_time - start_time:4.2f} segundos.")
    
    except Exception as e:
        print(f"Ocorreu um erro ao gerar o arquivo '{filename}': {e}")

# Funções públicas de geração chamadas pelo main.py
def gera_arquivo_FUNCIONARIOS_paralelo(filename, num_registros, record_size_bytes, chunk_por_cpu=5):
    _gerador_paralelo_orchestrator(filename, num_registros, record_size_bytes, _gera_chunk_de_FUNCIONARIOS, DADOS_AMOSTRA_NOME, chunk_por_cpu)

def gera_arquivo_PACIENTES_paralelo(filename, num_registros, record_size_bytes, chunk_por_cpu=5):
    _gerador_paralelo_orchestrator(filename, num_registros, record_size_bytes, _gera_chunk_de_PACIENTES, DADOS_AMOSTRA_NOME, chunk_por_cpu)

def gera_arquivo_VACINAS_paralelo(filename, num_registros, record_size_bytes, chunk_por_cpu=5):
    _gerador_paralelo_orchestrator(filename, num_registros, record_size_bytes, _gera_chunk_de_VACINAS, DADOS_AMOSTRA_VACINA, chunk_por_cpu)


# ORDENAÇÃO EXTERNA

def _quicksort_in_ram_generic(arr):
    # Função auxiliar para ordenar chunks em RAM.
    try:
        arr.sort() # Tenta usar o __lt__ da classe
        return arr
    except TypeError:
        # Fallback se __lt__ não estiver definido
        arr.sort(key=lambda x: getattr(x, x._fields_[0][0]))
        return arr


def mergesort_file(main_filename, structure_class, record_size_bytes, chunk_records_count):
    start_time = time.perf_counter()
    print(f"\nFASE 1: Iniciando Mergesort de '{main_filename}'...")
    print(f"Registros por chunk (RAM): {chunk_records_count:,}")
    
    chunk_files = [] # Lista para guardar nomes dos arquivos temporários

    try:
        chunk_num = 0
        total_records = 0
        
        with open(main_filename, "rb") as f_main:
            while True:
                records_in_memory = []
                for _ in range(chunk_records_count):
                    buffer = f_main.read(record_size_bytes)
                    if not buffer:
                        break
                    records_in_memory.append(structure_class.from_buffer_copy(buffer))
                
                if not records_in_memory:
                    break # Fim do arquivo principal

                # Ordena o chunk em RAM
                records_in_memory = _quicksort_in_ram_generic(records_in_memory)
                
                # Salva o chunk ordenado
                chunk_name = f"__chunk_sorted_{chunk_num}.dat"
                chunk_files.append(chunk_name)
                
                with open(chunk_name, "wb") as f_chunk:
                    for record in records_in_memory:
                        f_chunk.write(record)
                
                print(f"  -> Chunk {chunk_num} ({len(records_in_memory)} regs) ordenado e salvo.")
                total_records += len(records_in_memory)
                chunk_num += 1
        
        print(f"  -> Fase 1 concluída: {total_records:,} registros divididos em {len(chunk_files)} chunks.")

        if not chunk_files:
            print("Arquivo principal está vazio. Abortando.")
            return

        # K-Way Merge
        print("\nFASE 2: Mesclando chunks ordenados...")
        
        # Min-Heap para guardar (registro, indice_do_chunk)
        min_heap = []
        open_chunk_files = [] 
        
        try:
            # Abre todos os chunks e lê o primeiro registro de cada
            for i, chunk_name in enumerate(chunk_files):
                f = open(chunk_name, "rb")
                open_chunk_files.append(f)
                
                buffer = f.read(record_size_bytes)
                if buffer:
                    record = structure_class.from_buffer_copy(buffer)
                    # Adiciona (registro, indice) no heap
                    heapq.heappush(min_heap, (record, i))

            # Abre o arquivo de saída (substitui o original)
            with open(main_filename, "wb") as f_out:
                registros_escritos = 0
                while min_heap:
                    # Pega o menor registro de todos
                    smallest_record, chunk_index = heapq.heappop(min_heap)
                    
                    # Escreve no arquivo final
                    f_out.write(smallest_record)
                    registros_escritos += 1

                    # Lê o próximo registro do chunk de onde o menor saiu
                    f_chunk = open_chunk_files[chunk_index]
                    next_buffer = f_chunk.read(record_size_bytes)
                    
                    if next_buffer:
                        # Se houver próximo, adiciona no heap
                        next_record = structure_class.from_buffer_copy(next_buffer)
                        heapq.heappush(min_heap, (next_record, chunk_index))
                    # Se não houver, o arquivo desse chunk acabou
                
                print(f"  -> Merge concluído. {registros_escritos:,} registros escritos.")

        finally:
            # Garante que todos os file handles dos chunks sejam fechados
            for f in open_chunk_files:
                f.close()

    except FileNotFoundError:
        print(f"Erro: Arquivo principal '{main_filename}' não encontrado.")
        _log_operacao(f"Falha no Mergesort: Arquivo '{main_filename}' não encontrado.", "ERRO")
        return
    except Exception as e:
        print(f"Ocorreu um erro inesperado no Mergesort: {e}")
        _log_operacao(f"Falha no Mergesort: {e}", "CRÍTICO")
    finally:
        # Limpar os arquivos temporários
        print("\nFASE 3: Limpando arquivos temporários...")
        cleaned_count = 0
        for chunk_name in chunk_files:
            if os.path.exists(chunk_name):
                os.remove(chunk_name)
                cleaned_count += 1
        print(f"  -> {cleaned_count} arquivos chunk removidos.")

    end_time = time.perf_counter()
    print(f"\nMergesort de '{main_filename}' concluído!")
    print(f"Tempo total: {end_time - start_time:.2f} segundos.")
    _log_operacao(f"Mergesort de '{main_filename}' concluído. Duração: {end_time - start_time:.2f}s", "INFO")

# EMBARALHAMENTO EXTERNO

def fat_scramble_generic(main_filename, record_size_bytes, chunk_records_count):
    print(f"Iniciando embaralhamento externo de '{main_filename}'...")
    start_time = time.perf_counter()
    chunk_files = [] # Nomes dos arquivos temporários
    
    try:
        # Quebrar, embaralhar chunks em RAM e salvar
        print(f"\nPASSO 1: Lendo e embaralhando chunks de {chunk_records_count} registros...")
        chunk_num = 0
        total_records = 0
        
        with open(main_filename, "rb") as f_main:
            while True:
                records_in_memory = []
                for _ in range(chunk_records_count):
                    buffer = f_main.read(record_size_bytes)
                    if not buffer:
                        break
                    records_in_memory.append(buffer) # Lê bytes brutos
                
                if not records_in_memory:
                    break

                # Embaralha o chunk em RAM
                random.shuffle(records_in_memory)
                
                # Salva o chunk embaralhado
                chunk_name = f"__chunk_scrambled_{chunk_num}.dat"
                chunk_files.append(chunk_name)
                
                with open(chunk_name, "wb") as f_chunk:
                    for record_buffer in records_in_memory:
                        f_chunk.write(record_buffer)

                print(f"  -> Chunk {chunk_num} ({len(records_in_memory)} regs) embaralhado e salvo.")
                total_records += len(records_in_memory)
                chunk_num += 1

        if not chunk_files:
            print("Arquivo principal está vazio. Abortando.")
            return

        # Remontar o arquivo, com chunks em ordem aleatória
        print("\nPASSO 2: Remontando arquivo principal com chunks em ordem aleatória...")
        
        # Embaralha a ordem dos chunks
        random.shuffle(chunk_files)
        
        registros_escritos = 0
        with open(main_filename, "wb") as f_out: # Sobrescreve o original
            for i, chunk_name in enumerate(chunk_files):
                print(f"  -> Escrevendo chunk {i+1}/{len(chunk_files)} (Arquivo: {chunk_name})...")
                with open(chunk_name, "rb") as f_chunk:
                    while True:
                        buffer = f_chunk.read(4096) # Lê em pedaços de 4KB
                        if not buffer:
                            break
                        f_out.write(buffer)
                        registros_escritos += len(buffer)
        
        print(f"  -> Remontagem concluída. {registros_escritos // record_size_bytes} registros escritos.")

    except FileNotFoundError:
        print(f"Erro: Arquivo principal '{main_filename}' não encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado no fat_scramble: {e}")
    finally:
        # Limpar
        print("\nPASSO 3: Limpando arquivos temporários...")
        cleaned_count = 0
        for chunk_name in chunk_files:
            if os.path.exists(chunk_name):
                os.remove(chunk_name)
                cleaned_count += 1
        print(f"  -> {cleaned_count} arquivos chunk removidos.")

    end_time = time.perf_counter()
    print(f"\nEmbaralhamento de '{main_filename}' concluído!")
    print(f"Tempo total: {end_time - start_time:.2f} segundos.")


# FUNÇÕES DE ÍNDICE

def reconstruir_indice_paciente():
    # Varre 'aplicacoes.dat' e cria um novo arquivo de índice 'idx_paciente_aplic.dat'.    

    try:
        from . import models
    except ImportError:
        print("Erro fatal: 'models.py' não encontrado. Não é possível reconstruir o índice.")
        return

    print("Iniciando reconstrução do índice 'idx_paciente_aplicacao.dat'...")
    start_time = time.perf_counter()
    
    indice_em_memoria = []
    total_apps = 0
    
    try:
        # Ler todas as aplicações (leitura sequencial)
        with open(models.FILE_APLICACOES, "rb") as f:
            while True:
                buffer = f.read(models.RECORD_SIZE_APLIC)
                if not buffer:
                    break
                app = AplicacaoVacina.from_buffer_copy(buffer)
                
                # Cria o registro de índice
                novo_indice = IndicePacienteAplicacao(
                    cod_paciente_fk=app.cod_paciente_fk,
                    cod_aplicacao_fk=app.cod_aplicacao
                )
                indice_em_memoria.append(novo_indice)
                total_apps += 1
        
        if total_apps == 0:
            print("Nenhuma aplicação para indexar.")
            return

        print(f"  -> {total_apps} registros lidos. Ordenando índice em RAM...")

        # Ordenar o índice em memória (pelo cod_paciente_fk)
        indice_em_memoria.sort(key=lambda x: x.cod_paciente_fk)
        
        # Escrever o índice ordenado no arquivo
        with open(models.FILE_IDX_PACIENTE_APLIC, "wb") as f_idx:
            for item in indice_em_memoria:
                f_idx.write(item)
        
        duration = time.perf_counter() - start_time
        print(f"  -> Índice reconstruído e salvo com sucesso! ({duration:.2f}s)")
        
        # Logar a operação
        _log_operacao(f"Índice '{models.FILE_IDX_PACIENTE_APLIC}' reconstruído. {total_apps} registros.", "INFO")

    except FileNotFoundError:
        print(f"Erro: Arquivo '{models.FILE_APLICACOES}' não encontrado. Não foi possível construir o índice.")
        _log_operacao(f"Falha ao reconstruir índice: '{models.FILE_APLICACOES}' não encontrado.", "ERRO")
    except Exception as e:
        print(f"Erro ao reconstruir índice: {e}")
        _log_operacao(f"Falha ao reconstruir índice: {e}", "CRÍTICO")

# FUNÇÕES DE VERIFICAÇÃO

def verifica_ordenacao(filename, structure_class, record_size_bytes):
    # Verifica se um arquivo está ordenado pelo cod.
    
    print(f"Verificando ordenação de '{filename}'...")
    try:
        with open(filename, "rb") as f:
            key_field_name = structure_class._fields_[0][0]
            
            last_key = -float('inf')
            count = 0
            
            while True:
                buffer = f.read(record_size_bytes)
                if not buffer:
                    break
                
                record = structure_class.from_buffer_copy(buffer)
                current_key = getattr(record, key_field_name)
                
                if current_key < last_key:
                    print(f"  -> Erro de ordenação: Registro {count} (ID {current_key}) < Registro anterior (ID {last_key})")
                    _log_operacao(f"Verificação falhou: '{filename}' está DESORDENADO.", "ERRO")
                    return False
                
                last_key = current_key
                count += 1
            
            print(f"  -> Verificação concluída: '{filename}' ({count} registros) está ordenado.")
            _log_operacao(f"Verificação OK: '{filename}' está ordenado.", "INFO")
            return True

    except FileNotFoundError:
        print(f"  -> Aviso: Arquivo '{filename}' não encontrado para verificação.")
        return False # Se não existe, não está ordenado
    except Exception as e:
        print(f"  -> Erro ao verificar ordenação de '{filename}': {e}")
        return False
    
    
def gerar_lote_aplicacoes_aleatorias(quantidade=1000, paciente_id_fixo=None):
    # Gera registros de aplicações para debug
    # Se paciente_id_fixo informado, gera todas as aplicações para este paciente.
    
    msg_target = f"para o Paciente {paciente_id_fixo}" if paciente_id_fixo else "para pacientes aleatórios"
    print(f"Gerando {quantidade} aplicações aleatórias {msg_target}...")
    
    try:
        # Descobrir os limites dos IDs existentes
        if not os.path.exists(models.FILE_PACIENTES) or not os.path.exists(models.FILE_VACINAS) or not os.path.exists(models.FILE_FUNCIONARIOS):
            return False, "Arquivos de dados principais não encontrados."

        max_pac = os.path.getsize(models.FILE_PACIENTES) // models.RECORD_SIZE_PAC
        max_vac = os.path.getsize(models.FILE_VACINAS) // models.RECORD_SIZE_VAC
        max_func = os.path.getsize(models.FILE_FUNCIONARIOS) // models.RECORD_SIZE_FUNC

        if max_pac == 0 or max_vac == 0 or max_func == 0:
            return False, "As bases de dados estão vazias. Gere os dados principais primeiro."

        # Passado um ID fixo: valida se está dentro do range
        if paciente_id_fixo and (paciente_id_fixo < 1 or paciente_id_fixo > max_pac):
            return False, f"ID de Paciente {paciente_id_fixo} é inválido (Máx: {max_pac})."

        buffer = bytearray()
        
        # Próximo ID de aplicação
        try:
             next_id = (os.path.getsize(models.FILE_APLICACOES) // models.RECORD_SIZE_APLIC) + 1
        except FileNotFoundError:
             next_id = 1

        for i in range(quantidade):
            cod_app = next_id + i
            
            if paciente_id_fixo:
                cod_pac = paciente_id_fixo
            else:
                cod_pac = random.randint(1, max_pac)
                
            cod_vac = random.randint(1, max_vac)
            cod_func = random.randint(1, max_func)
            
            # Data aleatória
            dia = random.randint(1, 28)
            mes = random.randint(1, 12)
            ano = random.randint(2020, 2025)
            data_app = f"{dia:02d}/{mes:02d}/{ano}"

            nova_app = models.AplicacaoVacina(
                cod_app, cod_pac, cod_vac, cod_func, data_app.encode('utf-8')
            )
            buffer.extend(nova_app)

        # Escrever no disco
        with open(models.FILE_APLICACOES, "ab") as f:
            f.write(buffer)
            
        _log_operacao(f"Geração em lote: {quantidade} aplicações inseridas ({msg_target}).", "INFO")
        return True, f"{quantidade} aplicações geradas com sucesso!"

    except Exception as e:
        msg = f"Erro na geração aleatória: {e}"
        _log_operacao(msg, "ERRO")
        print(msg)
        return False, msg