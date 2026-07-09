import csv
import re
import os


def parse_sc_file(filepath):
    """Lê o arquivo .sc e retorna as linhas e um mapeamento do estado atual."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Regex para extrair textos (coluna A) e valores (coluna B)
    re_string = re.compile(r'rightstring A(\d+) = "(.*)"')
    re_val = re.compile(r'let B(\d+) = ([\d\.]+)')
    
    state = {'A': {}, 'B': {}, 'lines': lines}
    
    for idx, line in enumerate(lines):
        match_str = re_string.search(line)
        if match_str:
            row = int(match_str.group(1))
            val = match_str.group(2)
            state['A'][row] = {'val': val, 'line_idx': idx}
            
        match_val = re_val.search(line)
        if match_val:
            row = int(match_val.group(1))
            val = float(match_val.group(2))
            state['B'][row] = {'val': val, 'line_idx': idx}
            
    return state

def save_sc_file(filepath, lines):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def get_category_bounds(state, category_name):
    """Encontra onde uma categoria começa e onde a próxima categoria começa."""
    cat_row_start = None
    next_cat_row = 9999 # Um limite alto arbitrário
    
    rows_A = sorted(state['A'].keys())
    
    for r in rows_A:
        val = state['A'][r]['val']
        if val == f"_{category_name.upper()}":
            cat_row_start = r
        elif cat_row_start is not None and r > cat_row_start and val.startswith("_"):
            next_cat_row = r
            break
            
    return cat_row_start, next_cat_row

def main(sc_file, csv_file):
    state = parse_sc_file(sc_file)
    lines = state['lines']
    
    # Lendo as compras do CSV
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = row['Item']
            categoria = row['Categoria']
            valor = float(row['Valor'])
            
            cat_start, cat_end = get_category_bounds(state, categoria)
            
            if cat_start is None:
                print(f"Aviso: Categoria _{categoria.upper()} não encontrada no main.sc. Pulando {item}.")
                continue
                
            # Verifica se o item já existe dentro dessa categoria
            item_found_row = None
            for r in range(cat_start + 1, cat_end):
                if r in state['A'] and state['A'][r]['val'].lower() == item.lower():
                    item_found_row = r
                    break
            
            if item_found_row:
                # O item existe, vamos somar o valor
                current_val = state['B'].get(item_found_row, {'val': 0.0})['val']
                new_val = current_val + valor
                
                # Se já tinha um 'let B...', atualiza a linha
                if item_found_row in state['B']:
                    line_idx = state['B'][item_found_row]['line_idx']
                    lines[line_idx] = f"let B{item_found_row} = {new_val:.2f}\n"
                else:
                    # Se só tinha o nome em A, mas B estava vazio, anexa o comando no final
                    lines.append(f"let B{item_found_row} = {new_val:.2f}\n")
                
                # Atualiza o estado na memória para as próximas iterações
                state['B'][item_found_row] = {'val': new_val, 'line_idx': -1}
                print(f"Atualizado: {item} (Linha {item_found_row}) -> R$ {new_val:.2f}")
                
            else:
                # O item não existe, precisa achar uma linha vazia (buraco) na categoria
                empty_row = None
                for r in range(cat_start + 1, cat_end):
                    if r not in state['A']:
                        empty_row = r
                        break
                        
                if empty_row:
                    # Injeta as instruções de criação no final do arquivo
                    # (o sc-im executa na ordem, então adicionar no fim sobrescreve e aloca corretamente)
                    lines.append(f'rightstring A{empty_row} = "{item}"\n')
                    lines.append(f"let B{empty_row} = {valor:.2f}\n")
                    
                    # Atualiza o estado
                    state['A'][empty_row] = {'val': item, 'line_idx': -1}
                    state['B'][empty_row] = {'val': valor, 'line_idx': -1}
                    print(f"Novo item adicionado: {item} na linha {empty_row}")
                else:
                    print(f"Erro: Sem linhas vazias na categoria _{categoria.upper()} para o item {item}.")

    # Salva o resultado final (poderia salvar num main_new.sc para segurança)
    save_sc_file(sc_file, lines)
    print("Merge concluído!")

if __name__ == "__main__":
    import argparse

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
