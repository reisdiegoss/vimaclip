import sqlite3
import os

db_path = r"c:\Users\Diego Reis\Documents\DEV\Clipes\main-backend\db\vimaclip.db"

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Adiciona a coluna clips_count se não existir
        cursor.execute("ALTER TABLE video ADD COLUMN clips_count INTEGER DEFAULT 0")
        
        conn.commit()
        conn.close()
        print("Coluna clips_count adicionada com sucesso ao banco de dados vimaclip.db!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("A coluna clips_count já existe.")
        else:
            print(f"Erro ao atualizar banco: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")
else:
    print(f"Banco de dados não encontrado em: {db_path}")
