import subprocess
import json
import os
from datetime import datetime

def executar_comando(comando):
    """Executa o comando no terminal e retorna o resultado de forma segura"""
    try:
        resultado = subprocess.check_output(comando, shell=True, stderr=subprocess.DEVNULL, text=True)
        return resultado.strip()
    except Exception:
        return "N/A"

def obter_dados_hardware():
    # 1. Serial da Placa-Mãe (Tenta duas formas diferentes se uma falhar)
    serial_mb = executar_comando("sudo dmidecode -s baseboard-serial-number")
    if serial_mb in ["N/A", "None", "To be filled by O.E.M.", ""]:
        serial_mb = executar_comando("sudo dmidecode -s system-serial-number")

    # 2. CPU
    cpu = executar_comando("lscpu | grep 'Model name' | cut -d ':' -f 2 | sed 's/^ *//g'")

    # 3. RAM
    ram_total = executar_comando("awk '/MemTotal/ {printf \"%.0f GB\", $2/1024/1024}' /proc/meminfo")
    slots_ocupados = executar_comando("sudo dmidecode -t memory | grep -c 'Size: [0-9]'")
    slots_total = executar_comando("sudo dmidecode -t memory | grep 'Number Of Devices' | awk '{print $4}'")

    # 4. Discos (Lê apenas discos reais, ignorando dispositivos virtuais)
    discos_raw = executar_comando("lsblk -d -o NAME,SIZE,MODEL,TYPE -J")
    lista_discos = []
    try:
        if discos_raw != "N/A":
            discos_json = json.loads(discos_raw)
            for dev in discos_json.get('blockdevices', []):
                # Ignora a pen drive se o sistema a marcar como loop ou read-only
                if dev.get('type') == 'disk' and not dev.get('name').startswith('loop'):
                    lista_discos.append({
                        "tamanho": dev.get('size'),
                        "modelo": dev.get('model', 'Desconhecido').strip()
                    })
    except:
        lista_discos = [{"erro": "Não foi possível listar os discos"}]

    return {
        "data_verificacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "numero_serie_mb": serial_mb,
        "cpu": cpu,
        "ram_total": ram_total,
        "ram_slots_ocupados": slots_ocupados,
        "ram_slots_total": slots_total,
        "discos": lista_discos
    }

def main():
    os.system('clear')
    print("========================================")
    print("   A INICIAR DIAGNÓSTICO DE HARDWARE    ")
    print("========================================\n")
    print("A analisar componentes. Aguarde uns segundos...\n")
    
    novos_dados = obter_dados_hardware()
    
    # O "Truque de Mestre": Encontrar a pen drive original no Debian Live
    caminho_pen = "/lib/live/mount/medium"
    caminho_arquivo = os.path.join(caminho_pen, "inventory.json")
    
    # Fallback se a pen não for encontrada ali, salva na pasta atual
    if not os.path.exists(caminho_pen):
        caminho_arquivo = "inventory.json"
        
    # Lógica de Append (Adicionar sem apagar os PCs anteriores)
    inventario = []
    if os.path.exists(caminho_arquivo):
        try:
            with open(caminho_arquivo, 'r') as f:
                inventario = json.load(f)
        except:
            pass # Se o ficheiro estiver corrompido ou vazio, começa uma nova lista
            
    inventario.append(novos_dados)
    
    # Tenta salvar diretamente na Pen Drive
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(inventario, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        
    os.system('clear')
    print("========================================")
    print("        DADOS EXTRAÍDOS DO PC           ")
    print("========================================")
    print(json.dumps(novos_dados, indent=4, ensure_ascii=False))
    print("========================================\n")
    
    print("✅ VERIFICADO COM SUCESSO!")
    print(f"Total de PCs registados na pen: {len(inventario)}\n")
    print("Pode retirar a Pen Drive.\n")
    
    input("Pressione [ENTER] para desligar o computador...")
    os.system("sudo poweroff")

if __name__ == "__main__":
    main()