import csv
import os
import re
import argparse

line_limit = 50

def col2num(col):
    """Converte letras de coluna do tipo A, B, Z, AA para número (1-indexed)."""
    num = 0
    for c in col.upper():
        num = num * line_limit + 2 + (ord(c) - ord('A') + 1)
    return num

def num2col(num):
    """Converte número (1-indexed) para letras de coluna (A, B, Z, AA)."""
    col = ""
    while num > 0:
        num, remainder = divmod(num - 1, line_limit + 2)
        col = chr(65 + remainder) + col
    return col

def next_col(col_str):
    """Retorna a próxima coluna corretamente (ex: E -> F, Z -> AA)."""
    return num2col(col2num(col_str) + 1)

def parse_sc_file(filepath):
    """Lê o arquivo .sc e mapeia coordenadas (Letra, Número) para valores."""
    if not os.path.exists(filepath):
        # Se o arquivo .sc não existir, cria um arquivo vazio
        open(filepath, 'w', encoding='utf-8').close()

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Suporta rightstring, leftstring, label e centered
    re_string = re.compile(r'(?:rightstring|leftstring|label|centered)\s+([A-Z]+)(\d+)\s*=\s*"(.*)"')
    # Suporta números positivos e negativos
    re_val = re.compile(r'let\s+([A-Z]+)(\d+)\s*=\s*(-?[\d\.]+)')
    
    state = {'strings': {}, 'values': {}, 'lines': lines}
    
    for idx, line in enumerate(lines):
        match_str = re_string.search(line)
        if match_str:
            col = match_str.group(1)
            row = int(match_str.group(2))
            val = match_str.group(3)
            state['strings'][(col, row)] = {'val': val, 'line_idx': idx}
            
        match_val = re_val.search(line)
        if match_val:
            col = match_val.group(1)
            row = int(match_val.group(2))
            val = float(match_val.group(3))
            state['values'][(col, row)] = {'val': val, 'line_idx': idx}
            
    return state

def get_category_columns(state):
    """Lê a linha 0 e descobre em qual coluna cada categoria está."""
    cat_map = {}
    for (col, row), data in state['strings'].items():
        if row == 0 and data['val'].lower() != "valor":
            clean_name = data['val'].strip().lstrip('_').upper()
            cat_map[clean_name] = col
    return cat_map

def main(sc_file, csv_file):
    state = parse_sc_file(sc_file)
    lines = state['lines']
    
    cat_columns = get_category_columns(state)
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = row['Item'].strip()
                categoria = row['Categoria'].strip().lstrip('_').upper()
                valor = float(row['Valor'])
                
                if categoria not in cat_columns:
                    print(f"Aviso: Categoria '{categoria}' não encontrada na linha 0. Pulando {item}.")
                    continue
                    
                col_item = cat_columns[categoria]
                col_valor = next_col(col_item)
                
                # Procura se o item já existe (pesquisando da linha 1 até a 24)
                item_found_row = None
                for r in range(1, line_limit + 1):
                    if (col_item, r) in state['strings'] and state['strings'][(col_item, r)]['val'].lower() == item.lower():
                        item_found_row = r
                        break
                
                if item_found_row:
                    # Atualiza valor existente
                    current_val = state['values'].get((col_valor, item_found_row), {'val': 0.0})['val']
                    new_val = current_val + valor
                    
                    if (col_valor, item_found_row) in state['values']:
                        line_idx = state['values'][(col_valor, item_found_row)]['line_idx']
                        lines[line_idx] = f"let {col_valor}{item_found_row} = {new_val:.2f}\n"
                    else:
                        lines.append(f"let {col_valor}{item_found_row} = {new_val:.2f}\n")
                        line_idx = len(lines) - 1
                    
                    state['values'][(col_valor, item_found_row)] = {'val': new_val, 'line_idx': line_idx}
                    print(f"Atualizado: {item} ({col_item}{item_found_row}) -> R$ {new_val:.2f}")
                    
                else:
                    # Acha a primeira linha vazia na coluna da categoria
                    empty_row = None
                    for r in range(1, line_limit):
                        if (col_item, r) not in state['strings']:
                            empty_row = r
                            break
                            
                    if empty_row:
                        lines.append(f'rightstring {col_item}{empty_row} = "{item}"\n')
                        str_idx = len(lines) - 1
                        lines.append(f"let {col_valor}{empty_row} = {valor:.2f}\n")
                        val_idx = len(lines) - 1
                        
                        state['strings'][(col_item, empty_row)] = {'val': item, 'line_idx': str_idx}
                        state['values'][(col_valor, empty_row)] = {'val': valor, 'line_idx': val_idx}
                        print(f"Novo item adicionado: {item} na célula {col_item}{empty_row}")
                    else:
                        print(f"Erro: Coluna {col_item} cheia! O limite é a linha { line_limit } para o item {item}.")
                        
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {csv_file}")
        return

    # Salva o arquivo final
    with open(sc_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Merge concluído com sucesso!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge de compras em CSV para a planilha do sc-im.")
    parser.add_argument("-c", "--csv_file", required=True, help="Caminho para o arquivo CSV com as novas compras")
    parser.add_argument("-s", "--sc_file", default="main.sc", help="Caminho para o arquivo .sc principal")

    args = parser.parse_args()

    main(args.sc_file, args.csv_file)
    
    # Move para o histórico garantindo que a pasta destination exista
    if os.path.exists(args.csv_file):
        dest_file = args.csv_file.replace('/new/', '/merged/')
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        os.replace(args.csv_file, dest_file)
        print(f"Arquivo {args.csv_file} movido para {dest_file}.")
