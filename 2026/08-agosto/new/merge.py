import csv
import re


def parse_sc_file(filepath):
    """Lê o arquivo .sc e mapeia coordenadas (Letra, Número) para valores."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Regex agora captura a letra da coluna separada do número da linha
    re_string = re.compile(r'rightstring ([A-Z]+)(\d+) = "(.*)"')
    re_val = re.compile(r'let ([A-Z]+)(\d+) = ([\d\.]+)')
    
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
            # Remove o '_' do início (se houver) e deixa tudo maiúsculo para padronizar
            clean_name = data['val'].lstrip('_').upper()
            cat_map[clean_name] = col
    return cat_map

def next_col(col_letter):
    """Pula para a próxima coluna (ex: de E para F) para colocar o valor."""
    return chr(ord(col_letter) + 1)

def main(sc_file, csv_file):
    state = parse_sc_file(sc_file)
    lines = state['lines']
    
    # Dicionário: {'RECEITAS': 'A', 'DESPESAS FIXAS': 'C', 'COMIDA': 'E', ...}
    cat_columns = get_category_columns(state)
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = row['Item']
                categoria = row['Categoria'].upper()
                valor = float(row['Valor'])
                
                if categoria not in cat_columns:
                    print(f"Aviso: Categoria '{categoria}' não achada na linha 0. Pulando {item}.")
                    continue
                    
                col_item = cat_columns[categoria]
                col_valor = next_col(col_item)
                
                # Procura se o item já existe (pesquisando da linha 1 até a 24)
                item_found_row = None
                for r in range(1, 25):
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
                    
                    state['values'][(col_valor, item_found_row)] = {'val': new_val, 'line_idx': -1}
                    print(f"Atualizado: {item} ({col_item}{item_found_row}) -> R$ {new_val:.2f}")
                    
                else:
                    # Acha a primeira linha vazia (buraco) na coluna da categoria
                    empty_row = None
                    for r in range(1, 25):
                        if (col_item, r) not in state['strings']:
                            empty_row = r
                            break
                            
                    if empty_row:
                        lines.append(f'rightstring {col_item}{empty_row} = "{item}"\n')
                        lines.append(f"let {col_valor}{empty_row} = {valor:.2f}\n")
                        
                        state['strings'][(col_item, empty_row)] = {'val': item, 'line_idx': -1}
                        state['values'][(col_valor, empty_row)] = {'val': valor, 'line_idx': -1}
                        print(f"Novo item adicionado: {item} na célula {col_item}{empty_row}")
                    else:
                        print(f"Erro: Coluna {col_item} cheia! O limite é a linha 24 para o item {item}.")
                        
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {csv_file}")

    # Salva o arquivo final
    with open(sc_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Merge concluído!")

if __name__ == "__main__":
    import argparse, os

    # Configuração do parser de argumentos
    parser = argparse.ArgumentParser(description="Merge de compras em CSV para a planilha do sc-im.")
    
    # Argumento obrigatório para o CSV
    parser.add_argument(
        "-c", "--csv_file", 
        help="Caminho para o arquivo CSV com as novas compras (ex: new/compra.csv)"
    )
    
    # Argumento opcional para o arquivo .sc (caso você tenha planilhas de meses diferentes)
    parser.add_argument(
        "-s", "--sc_file", 
        default="main.sc", 
        help="Caminho para o arquivo .sc principal (padrão: main.sc)"
    )

    # Faz o parse dos argumentos digitados no terminal
    args = parser.parse_args()

    # Sobrescreve as variáveis globais usadas pela função main()
    sc_file = args.sc_file
    csv_file = args.csv_file

    main(sc_file, csv_file)
    os.replace(csv_file, csv_file.replace('new/', 'merged/'))
    print(f"Arquivo {csv_file} movido para histórico.")
