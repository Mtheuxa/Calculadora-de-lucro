from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from main import process_directory
from drive_service import DriveService

app = Flask(__name__)
CORS(app)

@app.route('/api/drive', defaults={'folder_id': 'root'}, methods=['GET'])
@app.route('/api/drive/<folder_id>', methods=['GET'])
def list_drive(folder_id):
    try:
        drive_srv = DriveService()
        items = drive_srv.list_directory(folder_id)
        
        folder_name = "Meu Drive"
        if folder_id != 'root':
            name = drive_srv.get_folder_name(folder_id)
            if name: folder_name = name
            
        return jsonify({"success": True, "data": items, "folder_name": folder_name, "folder_id": folder_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/preview', methods=['POST'])
def preview():
    data = request.json
    source_id = data.get('source_id')
    course_name = data.get('course_name')
    
    if not source_id:
        return jsonify({"error": "source_id is required"}), 400
        
    try:
        drive_srv = DriveService()
        results = process_directory(
            source_id=source_id, 
            dest_id=None, 
            drive_service=drive_srv, 
            allowed_courses=None, 
            dry_run=True, 
            course_name=course_name, 
            return_data=True
        )
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/run', methods=['POST'])
def run():
    data = request.json
    source_id = data.get('source_id')
    dest_id = data.get('dest_id')
    course_name = data.get('course_name')
    
    if not source_id:
        return jsonify({"error": "source_id is required"}), 400
        
    try:
        drive_srv = DriveService()
        root_dest = dest_id if dest_id else None
        
        process_directory(
            source_id=source_id, 
            dest_id=root_dest, 
            drive_service=drive_srv, 
            allowed_courses=None, 
            dry_run=False, 
            course_name=course_name, 
            return_data=False
        )
        return jsonify({"success": True, "message": "Automação finalizada com sucesso."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<file_id>', methods=['GET'])
def download_file(file_id):
    try:
        drive_srv = DriveService()
        file_name = drive_srv.get_folder_name(file_id) or "download"
        
        file_bytes = drive_srv.download_file_to_memory(file_id)
        if not file_bytes:
            return jsonify({"error": "Não foi possível baixar o arquivo (talvez seja um Google Doc ou não há permissão)"}), 400
            
        return send_file(
            file_bytes,
            as_attachment=True,
            download_name=file_name,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
