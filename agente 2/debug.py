from drive_service import DriveService
import sys

def debug_paths(folder_id):
    try:
        drive_srv = DriveService()
        print(f"Buscando na pasta: {folder_id}")
        count = 0
        for info in drive_srv.walk_folder(folder_id):
            print(info['path'])
            count += 1
            if count >= 30: # imprime os 30 primeiros
                break
        print(f"Total impresso: {count}")
    except Exception as e:
        print("Erro:", e)

if __name__ == '__main__':
    debug_paths("1CCAfj2zR02OVB6ZK8aKDSswSWWgN9d0Z")
