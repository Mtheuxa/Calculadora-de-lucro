import os
import json
import time
import schedule
from datetime import datetime

from auth import get_drive_service
from search import search_updated_files
from download import download_file

PROCESSED_FILE = 'processed.json'

def load_processed_files():
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_processed_files(processed):
    with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
        json.dump(processed, f, indent=4, ensure_ascii=False)

def run_agent():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando verificação do Google Drive...")
    
    # 1. Autenticar
    service = get_drive_service()
    if not service:
        print("Serviço do Google Drive indisponível. O arquivo credentials.json está correto?")
        return

    # 2. Buscar Arquivos
    arquivos = search_updated_files(service)
    
    if not arquivos:
        print("Nenhum arquivo encontrado que corresponda aos critérios (2026, 'plano de ensino', 'controle de ua').")
        return

    # 3. Carregar memória de arquivos já processados
    processed = load_processed_files()
    arquivos_novos_baixados = 0

    # 4. Processar e baixar apenas os novos/atualizados
    for arquivo in arquivos:
        file_id = arquivo['id']
        modified_time = arquivo.get('modifiedTime', '')
        
        # Baixa se nunca vimos esse arquivo ou se a data de modificação mudou
        if file_id not in processed or processed[file_id].get('modifiedTime') != modified_time:
            print(f"-> Arquivo pendente para download: {arquivo['name']} (Curso: {arquivo['curso']})")
            
            caminho_salvo = download_file(service, arquivo, base_dir="Downloads_Drive")
            
            if caminho_salvo:
                # Registra sucesso
                processed[file_id] = {
                    'name': arquivo['name'],
                    'curso': arquivo['curso'],
                    'modifiedTime': modified_time,
                    'download_path': caminho_salvo,
                    'downloaded_at': datetime.now().isoformat()
                }
                arquivos_novos_baixados += 1
                save_processed_files(processed)
        else:
            # Já baixamos esta versão específica
            pass
            
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Verificação concluída. {arquivos_novos_baixados} novos arquivos baixados.")

if __name__ == "__main__":
    print("==========================================================")
    print("      Agente Extrator do Google Drive - Inicializado      ")
    print("==========================================================")
    
    # Verifica credenciais antes de entrar no loop
    if not os.path.exists('credentials.json'):
        print("\nATENÇÃO: Você precisa colocar o arquivo 'credentials.json' na pasta:")
        print(os.path.abspath(os.path.dirname(__file__)))
        print("\nSiga as instruções para gerar este arquivo no Google Cloud Console.")
    else:
        # Executa a primeira vez imediatamente
        run_agent()
        
        # Agenda para rodar a cada 1 hora
        print("\nAgente programado para rodar a cada 1 hora.")
        print("Mantenha esta janela aberta. Pressione Ctrl+C para encerrar.")
        schedule.every(1).hours.do(run_agent)
        
        while True:
            schedule.run_pending()
            time.sleep(60) # Verifica a agenda a cada 60 segundos
