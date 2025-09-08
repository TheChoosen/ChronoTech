#!/usr/bin/env python3
"""
Serveur minimal pour test Kanban - Port 5025
Serveur ultra-simple sans dépendances complexes
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
import pymysql
from datetime import datetime

class KanbanHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/api/health':
            self.send_json({'status': 'healthy', 'server': 'minimal-kanban'})
        elif path == '/api/kanban-data':
            self.handle_kanban_data()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_headers()
        self.end_headers()
    
    def send_headers(self):
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def send_json(self, data):
        self.send_response(200)
        self.send_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    
    def handle_kanban_data(self):
        try:
            # Connexion directe à la base
            conn = pymysql.connect(
                host='192.168.50.101',
                user='gsicloud',
                password='TCOChoosenOne204$',
                database='bdm',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            cursor = conn.cursor()
            
            # Requête simple
            query = """
                SELECT wo.id, wo.claim_number, wo.status, wo.priority, wo.description,
                       wo.created_at, wo.customer_id,
                       c.name as customer_name,
                       t.name as technician_name
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN users t ON wo.assigned_technician_id = t.id
                ORDER BY wo.created_at DESC
            """
            
            cursor.execute(query)
            work_orders = cursor.fetchall()
            
            # Organiser par statut
            kanban_data = {
                'draft': [],
                'pending': [],
                'assigned': [],
                'in_progress': [],
                'completed': [],
                'cancelled': []
            }
            
            for wo in work_orders:
                status = wo.get('status', 'pending')
                if status not in kanban_data:
                    status = 'pending'
                
                kanban_data[status].append({
                    'id': wo['id'],
                    'claim_number': wo.get('claim_number', f"WO-{wo['id']}"),
                    'customer_name': wo.get('customer_name', f'Client {wo.get("customer_id", "?")}'),
                    'technician_name': wo.get('technician_name'),
                    'description': wo.get('description', ''),
                    'priority': wo.get('priority', 'medium'),
                    'status': status,
                    'created_at': wo.get('created_at', '').strftime('%Y-%m-%d %H:%M') if wo.get('created_at') else ''
                })
            
            cursor.close()
            conn.close()
            
            self.send_json({
                'success': True,
                'kanban_data': kanban_data,
                'total_count': len(work_orders),
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"📊 Données envoyées: {len(work_orders)} bons de travail")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            self.send_json({
                'success': False,
                'error': str(e)
            })

if __name__ == '__main__':
    print("🚀 Serveur minimal Kanban - Port 5025")
    server = HTTPServer(('0.0.0.0', 5025), KanbanHandler)
    server.serve_forever()
