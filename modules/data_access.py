import os
import ctypes
import time
from .models import (
    Funcionario, Paciente, Vacina, AplicacaoVacina, IndicePacienteAplicacao,
    RECORD_SIZE_FUNC, RECORD_SIZE_PAC, RECORD_SIZE_VAC, 
    RECORD_SIZE_APLIC, RECORD_SIZE_IDX_PAC
)
# FUNÇÕES DE LEITURA

def bin_seek_por_cod(filename: str, record_size: int, structure_class, target_id: int):
    # Busca binária genérica por ID
    start_time = time.perf_counter()
    comparisons = 0
    found_record = None

    if target_id <= 0:
        print("Erro: ID do registro deve ser positivo")
        return None

    try:
        with open(filename, "rb") as f:
            file_size = os.path.getsize(filename)
            num_records = file_size // record_size
            
            if num_records == 0:
                print(f"Arquivo '{filename}' está vazio.")
                return None

            low = 0
            high = num_records - 1

            while low <= high:
                comparisons += 1
                mid_index = (low + high) // 2
                
                f.seek(mid_index * record_size)
                buffer = f.read(record_size)
                
                if not buffer: 
                    break

                current_record = structure_class.from_buffer_copy(buffer)
                
                # Leitura genérica do primeiro campo
                # Acessa o nome do primeiro campo de _fields_ 
                key_field_name = current_record._fields_[0][0]
                current_id = getattr(current_record, key_field_name)

                if current_id == target_id:
                    found_record = current_record
                    break  # Encontrou
                elif target_id < current_id:
                    high = mid_index - 1
                else:
                    low = mid_index + 1
        
        duration = time.perf_counter() - start_time
        status = "Encontrado" if found_record else "Não Encontrado"
        print(f"[bin_seek] ID: {target_id} em '{filename}'. Status: {status}. Comps: {comparisons}. Duração: {duration:.6f}s")
        
        return found_record

    except FileNotFoundError:
        print(f"Erro: O arquivo '{filename}' não foi encontrado.")
        return None
    except Exception as e:
        print(f"Erro inesperado em bin_seek_por_cod: {e}")
        return None

def ler_sequencial(filename: str, record_size: int, structure_class):
    # Leitura sequencial
    print(f"Lendo sequencialmente o arquivo '{filename}'...")
    registros = []
    try:
        with open(filename, "rb") as f:
            while True:
                buffer = f.read(record_size)
                if not buffer:
                    break
                registros.append(structure_class.from_buffer_copy(buffer))
        
        print(f" -> {len(registros)} registros carregados.")
        return registros
        
    except FileNotFoundError:
        print(f"Erro: Arquivo '{filename}' não encontrado.")
        return []

# FUNÇÕES DE ESCRITA

def adicionar_registro(filename: str, registro):
    # Adiciona registro ao final. Requer ordenação
    try:
        # 'ab' = Append Binary (adiciona ao final, sem apagar)
        with open(filename, "ab") as f: 
            f.write(registro)
        return True
    except Exception as e:
        print(f"Erro ao adicionar registro em '{filename}': {e}")
        return False

def get_next_id(filename: str, record_size: int, structure_class) -> int:
    # Descobre o prox id
    try:
        if not os.path.exists(filename):
            return 1 # Arquivo não existe, primeiro ID é 1
            
        file_size = os.path.getsize(filename)
        if file_size == 0:
            return 1 # Arquivo existe, mas está vazio, primeiro ID é 1

        with open(filename, "rb") as f:
            # Pula para o início do último registro
            f.seek(-record_size, os.SEEK_END) 
            buffer = f.read(record_size)
            
            record = structure_class.from_buffer_copy(buffer)
            
            # Leitura genérica do primeiro campo
            key_field_name = record._fields_[0][0]
            last_id = getattr(record, key_field_name)
            
            return last_id + 1
            
    except Exception as e:
        print(f"Erro ao obter próximo ID de '{filename}': {e}")
        return 1

def sobrescrever_registro_por_cod(filename: str, record_size: int, target_id: int, novo_registro):
    # Sobrescreve registro. Requer ordenação prévia
    # Calcula a posição exata em bytes
    offset = (target_id - 1) * record_size
    
    try:
        # 'rb+' = Read/Write Binary. Não apaga o arquivo.
        with open(filename, "rb+") as f: 
            f.seek(offset) # Pula para a posição correta
            f.write(novo_registro) # Sobrescreve
        return True
    except FileNotFoundError:
        print(f"Erro: Arquivo '{filename}' não encontrado.")
        return False
    except Exception as e:
        print(f"Erro ao sobrescrever registro {target_id} em '{filename}': {e}")
        return False

def deletar_registro_por_cod(filename: str, record_size: int, target_id: int):
    #Sobrescreve registro
    offset = (target_id - 1) * record_size
    
    # Cria um registro vazio
    null_record = bytearray(record_size)
    
    try:
        with open(filename, "rb+") as f:
            f.seek(offset)
            f.write(null_record)
        return True
    except FileNotFoundError:
        print(f"Erro: Arquivo '{filename}' não encontrado.")
        return False
    except Exception as e:
        print(f"Erro ao deletar registro {target_id} em '{filename}': {e}")
        return False

def bin_seek_all_matches_in_index(filename: str, record_size: int, structure_class, target_id: int):
    # Busca binária retorna uma lista de valores correspondentes.
    # Ler o arquivo de índice onde um Paciente alvo pode ter várias Aplicações.
    
    matches = []
    try:
        if not os.path.exists(filename):
            return []

        with open(filename, "rb") as f:
            file_size = os.path.getsize(filename)
            num_records = file_size // record_size
            
            if num_records == 0:
                return []

            low = 0
            high = num_records - 1
            found_index = -1

            # Busca Binária para encontrar qualqer ocorrência do ID
            while low <= high:
                mid = (low + high) // 2
                f.seek(mid * record_size)
                buffer = f.read(record_size)
                record = structure_class.from_buffer_copy(buffer)
                
                # Assume que o primeiro campo é a chave de busca
                current_id = getattr(record, record._fields_[0][0]) 

                if current_id == target_id:
                    found_index = mid
                    break
                elif current_id < target_id:
                    low = mid + 1
                else:
                    high = mid - 1
            
            if found_index == -1:
                return [] # Paciente não encontrado
            
            # Backtracking para encontrar todos os IDs numa lista de registros iguais

            start_index = found_index
            while start_index > 0:
                f.seek((start_index - 1) * record_size)
                buffer = f.read(record_size)
                prev_record = structure_class.from_buffer_copy(buffer)
                prev_id = getattr(prev_record, prev_record._fields_[0][0])
                
                if prev_id == target_id:
                    start_index -= 1
                else:
                    break # O registro anterior é diferente e start_index é o primeiro
            
            # Coleta a partir do start_index
            f.seek(start_index * record_size)
            while True:
                buffer = f.read(record_size)
                if not buffer: 
                    break
                record = structure_class.from_buffer_copy(buffer)
                current_id = getattr(record, record._fields_[0][0])
                
                if current_id == target_id:
                    # Pega o segundo campo valor alvo: cod_aplicacao_fk
                    value_field = getattr(record, record._fields_[1][0])
                    matches.append(value_field)
                else:
                    break
                    
        return matches

    except Exception as e:
        print(f"Erro na busca indexada em '{filename}': {e}")
        return []