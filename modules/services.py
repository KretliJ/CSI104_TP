import time
import os

from . import data_access
from . import utils
from .models import * 
from . import models
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
except ImportError:
    print("Reportlab não instalado: pip install reportlab")
    canvas = None

# APLICAÇÃO DE VACINA

def registrar_aplicacao_sem_ordenar(paciente_id: int, vacina_id: int, funcionario_id: int, data_aplicacao: str):
 
    try:
        # USA O LOGGER DO 'UTILS'
        utils._log_operacao(f"Tentativa de aplicação: PAC={paciente_id}, VAC={vacina_id}, FUNC={funcionario_id}")
        
        # VERIFICAR SE AS ENTIDADES EXISTEM
        paciente = data_access.bin_seek_por_cod(FILE_PACIENTES, RECORD_SIZE_PAC, Paciente, paciente_id)
        if not paciente:
            msg = f"Falha: Paciente com ID {paciente_id} não encontrado."
            utils._log_operacao(msg, "ERRO")
            return (False, msg)

        vacina = data_access.bin_seek_por_cod(FILE_VACINAS, RECORD_SIZE_VAC, Vacina, vacina_id)
        if not vacina:
            msg = f"Falha: Vacina com ID {vacina_id} não encontrada."
            utils._log_operacao(msg, "ERRO")
            return (False, msg)

        func = data_access.bin_seek_por_cod(FILE_FUNCIONARIOS, RECORD_SIZE_FUNC, Funcionario, funcionario_id)
        if not func:
            msg = f"Falha: Funcionário com ID {funcionario_id} não encontrado."
            utils._log_operacao(msg, "ERRO")
            return (False, msg)

        # CRIAR O NOVO REGISTRO DE RELACIONAMENTO
        novo_id_aplicacao = data_access.get_next_id(FILE_APLICACOES, RECORD_SIZE_APLIC, AplicacaoVacina)
        
        nova_aplicacao = AplicacaoVacina(
            cod_aplicacao=novo_id_aplicacao,
            cod_paciente_fk=paciente_id,
            cod_vacina_fk=vacina_id,
            cod_funcionario_fk=funcionario_id,
            data_aplicacao=data_aplicacao.encode('utf-8')
        )

        # ADICIONAR O REGISTRO
        if data_access.adicionar_registro(FILE_APLICACOES, nova_aplicacao):
            msg = f"Sucesso: Aplicação {novo_id_aplicacao} registrada. (Arquivo {FILE_APLICACOES} agora desordenado)."
            utils._log_operacao(msg, "INFO")
            # Invalida o índice
            _invalidar_indice_paciente()
            return (True, msg)
        else:
            msg = f"Falha: Erro ao salvar aplicação {novo_id_aplicacao} no disco."
            utils._log_operacao(msg, "ERRO")
            return (False, msg)

    except Exception as e:
        utils._log_operacao(f"Erro inesperado em registrar_aplicacao: {e}", "CRÍTICO")
        return (False, f"Erro inesperado: {e}")

def _invalidar_indice_paciente():

    try:
        if os.path.exists(FILE_IDX_PACIENTE_APLIC):
            os.rename(FILE_IDX_PACIENTE_APLIC, FILE_IDX_PACIENTE_APLIC + ".invalid")
            utils._log_operacao(f"Índice '{FILE_IDX_PACIENTE_APLIC}' invalidado (requer reconstrução).", "AVISO")
    except Exception as e:
        utils._log_operacao(f"Falha ao invalidar índice '{FILE_IDX_PACIENTE_APLIC}': {e}", "ERRO")

# GERAÇÃO DE CARTÃO

def gerar_cartao_paciente_pdf(paciente_id: int):

    utils._log_operacao(f"Iniciando geração de PDF para PACIENTE ID={paciente_id}.")

    # Verifica índice
    if not os.path.exists(models.FILE_IDX_PACIENTE_APLIC):
        return False, "O índice não existe. O sistema precisa reordenar antes de gerar cartões."

    # Busca Paciente
    paciente = data_access.bin_seek_por_cod(models.FILE_PACIENTES, models.RECORD_SIZE_PAC, models.Paciente, paciente_id)
    if not paciente:
        return False, f"Paciente com ID {paciente_id} não encontrado."

    nome_paciente = paciente.nome.decode('utf-8').strip('\x00')
    cpf_paciente = paciente.cpf.decode('utf-8').strip('\x00')

    # Busca IDs das aplicações no índice
    aplicacoes_ids = data_access.bin_seek_all_matches_in_index(
        models.FILE_IDX_PACIENTE_APLIC, 
        models.RECORD_SIZE_IDX_PAC, 
        models.IndicePacienteAplicacao,
        paciente_id
    )

    # Configuração do diretório e arquivo
    pasta_destino = "Cartões"
    os.makedirs(pasta_destino, exist_ok=True)
    filename_pdf = os.path.join(pasta_destino, f"Cartao_Vacina_{paciente_id}_{nome_paciente.split()[0]}.pdf")

    try:
        c = canvas.Canvas(filename_pdf, pagesize=A4)
        width, height = A4
        
        # Cabeçalho
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "Cartão Nacional de Vacinação")
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 80, f"Paciente: {nome_paciente}")
        c.drawString(50, height - 100, f"ID: {paciente_id}  |  CPF: {cpf_paciente}")
        
        c.line(50, height - 110, width - 50, height - 110)

        # Listagem
        y_pos = height - 140
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Histórico de Aplicações:")
        y_pos -= 30
        
        if not aplicacoes_ids:
            c.setFont("Helvetica", 12)
            c.drawString(50, y_pos, "Nenhuma vacina registrada até o momento.")
        else:
            c.setFont("Helvetica", 10)
            for app_id in aplicacoes_ids:
                aplicacao = data_access.bin_seek_por_cod(models.FILE_APLICACOES, models.RECORD_SIZE_APLIC, models.AplicacaoVacina, app_id)
                
                if aplicacao:
                    vacina = data_access.bin_seek_por_cod(models.FILE_VACINAS, models.RECORD_SIZE_VAC, models.Vacina, aplicacao.cod_vacina_fk)
                    func = data_access.bin_seek_por_cod(models.FILE_FUNCIONARIOS, models.RECORD_SIZE_FUNC, models.Funcionario, aplicacao.cod_funcionario_fk)
                    
                    vac_nome = vacina.nome_fabricante.decode('utf-8').strip('\x00') if vacina else "Desconhecida"
                    lote = vacina.lote.decode('utf-8').strip('\x00') if vacina else "--"
                    data_vac = aplicacao.data_aplicacao.decode('utf-8').strip('\x00')
                    func_nome = func.nome.decode('utf-8').strip('\x00') if func else "N/A"

                    # Linha do registro
                    texto = f"DATA: {data_vac} | VACINA: {vac_nome} (Lote: {lote}) | APLICADOR: {func_nome}"
                    c.drawString(60, y_pos, texto)
                    y_pos -= 20
                    
                    if y_pos < 50: # Nova página se acabar o espaço
                        c.showPage()
                        y_pos = height - 50

        c.save()
        utils._log_operacao(f"PDF gerado com sucesso: {filename_pdf}", "INFO")
        return True, f"Cartão gerado com sucesso!\nSalvo em: {filename_pdf}"

    except Exception as e:
        msg = f"Erro ao gerar PDF: {e}"
        utils._log_operacao(msg, "ERRO")
        return False, msg