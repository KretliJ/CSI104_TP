# **CSI104-2025-02 - Proposta de Trabalho Final**

## *Discente: Jonas Elias Kretli*

<!-- Descrever um resumo sobre o trabalho. -->

### Resumo
 
  Este trabalho final consiste no desenvolvimento de um Sistema de Gestão de Vacinação, focado na manipulação de arquivos binários. O sistema simula um ambiente de banco de dados customizado, capaz de gerenciar grandes volumes de dados (funcionários, pacientes, vacinas e aplicações) utilizando estruturas de tamanho fixo, indexação e algoritmos de ordenação externa (em disco).

### 1. Tema

  Desenvolvimento de um sistema de informação para controle de vacinação com persistência em arquivos binários e interface gráfica.

### 2. Escopo
  
  O sistema entregue contempla as seguintes funcionalidades e características:
  
  * **Arquitetura:** 4 arquivos principais (`.dat`) para armazenar vacinas, funcionários, pacientes, e aplicações, além de um arquivo de log que registra as operações feitas.
  * **Manipulação de Arquivos:** Implementação de leitura sequencial e aleatória (Random Access) utilizando o módulo ctypes para mapeamento direto de estruturas em C.
  * **Algoritmos Avançados:**
    * **Busca Binária:** Para recuperação rápida de registros por chave primária.
    * **Ordenação Externa (Mergesort):** Implementação de K-Way Merge para ordenar arquivos maiores que a memória RAM disponível.
    * **Indexação:** Criação e reconstrução dinâmica de índices para relação Um-para-Muitos (Paciente -> Aplicações).
  * **Funcionalidades da Lógica de Negócio:**
    * Cadastro de aplicações de vacinas.
    * Geração de Cartão de Vacinação em PDF, contendo o histórico completo do paciente.
  * **Interface Gráfica (GUI):** Interface amigável desenvolvida com `tkinter`, com suporte a rolagem, logs de operação em tempo real e thread dedicada para operações de manipulação em massa (evita aparência de congelamento da tela).
  * **Performance:** Geração de massa de dados utilizando multiprocessamento para criação rápida de registros na quantidade de milhares ou mais.
  
<!-- Apresentar restrições de funcionalidades e de escopo. -->
### 3. Restrições

  * **Linguagem:** Python 3.14.
  * **Persistência:** Módulo `ctypes` (registros de tamanho fixo).
  * **Dados:** Criados exclusivamente de maneira aleatória dada a quantidade de registros dos arquivos operados.
    * Atualmente 10000 registros para vacinas, clientes e funcionários, podendo ser expandida.  
  * **Interface:** `tkinter` (Pacote nativo Python).
  * **Concorrência:** threading (para IO/Sort em background) e multiprocessing (para geração de dados).
  * **Relatórios:**
    * log em `.txt` para registro de operações.
    * `reportlab` para geração de PDFs.

<!-- Construir alguns protótipos para a aplicação, disponibilizá-los no Github e descrever o que foi considerado. //-->
### 4. Cronograma de Desenvolvimento

  v1.0 (07/11): Protótipo de estruturas de dado e funções básica de criação de arquivos.
  v1.2 (07/11): Definição das estruturas (models.py) e funções básicas de IO.
  v1.4 (14/11): Implementação do Mergesort e geração de dados paralela.
  v1.6 (20/11): Implementação da Interface Gráfica e conexão interna com serviços.
  v2.0 (25/11): Implementação da Indexação, Geração de PDF, Tela de Manutenção/Debug e correção de bugs de concorrência.
  
### 5. Referências

  * Material disciplina CSI104 - ALGORITMOS E ESTRUTURAS DE DADOS II.
  * Documentação Python (`ctypes`, `multiprocessing`, `tkinter`).
  * Documentação ReportLab (Geração de PDFs).

### 6. Instalação e Execução

  * Pré-requisitos
    * Python 3.13 ou superior
    * Git

 1. Clonar o repositório
    ```
    git clone https://github.com/KretliJ/CSI104_TP.git
    cd CSI104_TP
    ```
 2. Instalar Dependências:
    ```
    pip install reportlab
    ```
 3. Executar o arquivo principal:
    ```
    python main.py
    ```
Nota: Na primeira execução, o sistema irá criar automaticamente o diretório files/ e gerar os arquivos binários iniciais com dados de teste. Esse processo pode levar alguns segundos. Logs de INFO serão registrados e prints de debug serão mostrados no terminal.
