#!/bin/bash


#python3 merge.py -s caminho  -c caminho

caminho_arquivo="meutexto.txt"
destino="/caminho/para/destino"

nome_base=$(basename "$caminho_arquivo")

# Pega o timestamp de modificação do arquivo em segundos + nanossegundos (Epoch)
timestamp=$(date -r "$caminho_arquivo" +%s%N)

# Alternativa: se quiser o timestamp do momento exato em que o arquivo está sendo movido:
# timestamp=$(date +%s%N)

# Move o arquivo anexando o timestamp
mv "$caminho_arquivo" "$destino/${timestamp}_${nome_base}"

echo "Arquivo movido para: $destino/${timestamp}_${nome_base}"
