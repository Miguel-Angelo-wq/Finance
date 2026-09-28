import os

year = "2026"
#month = "07-julho"
month = "09-setembro"

dir_new = f"./{year}/{month}/new"
sc_file = f"./{year}/{month}/main.sc"

if os.path.exists(dir_new):
    for filename in os.listdir(dir_new):
        if filename.endswith(".csv"):
            # Passa o caminho completo do arquivo
            full_csv_path = os.path.join(dir_new, filename)
            os.system(f'python3 merge.py -c "{full_csv_path}" -s "{sc_file}"')
else:
    print(f"Diretório {dir_new} não encontrado.")
