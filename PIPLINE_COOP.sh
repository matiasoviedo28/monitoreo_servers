#!/bin/bash

LOG_FILE="logs.txt"
STATUS_FILE="server_status.txt"
CSV_FILE="monitoreando.csv"

declare -A SERVIDORES
declare -A TOLERANCIA_TIEMPO
declare -A ESTADO_SERVIDORES
declare -A ULTIMA_CAIDA
declare -A ULTIMA_RECUPERACION
declare -A TIEMPO_ACUMULADO
declare -A PING_VALORES

touch "$STATUS_FILE"
touch "$CSV_FILE"

# función para leer los servidores a monitorear.
# El csv monitoreando.csv debe tener el siguiente formato:

# name,ip,tolerancia
#"Google","192.168.1.100",1
#"Facebook","192.168.1.101",2

#La tolerancia es el tiempo que debe estar sin responder para considerarlo apagado.

cargar_servidores() {
    SERVIDORES=()
    TOLERANCIA_TIEMPO=()
    while IFS=, read -r NAME IP TOLERANCIA; do
        NAME=$(echo "$NAME" | tr -d '"')
        IP=$(echo "$IP" | tr -d '"')
        TOLERANCIA=$(echo "$TOLERANCIA" | tr -d '"')
        SERVIDORES["$NAME"]="$IP"
        TOLERANCIA_TIEMPO["$NAME"]="$TOLERANCIA"
    done < <(tail -n +2 "$CSV_FILE")
}

#activar el entorno virtual
source /home/ubuntu/COOP/venv/bin/activate

# iniciar Flask en segundo plano
pkill -f web_monitoring.py
nohup python3 /home/ubuntu/COOP/web_monitoring.py > /home/ubuntu/COOP/web_monitoring.log 2>&1 &

# LOOP
while true; do
    cargar_servidores
    > "$STATUS_FILE"  # Limpiar archivo antes de actualizar
    
    for NOMBRE in "${!SERVIDORES[@]}"; do
        IP="${SERVIDORES[$NOMBRE]}"
        
        echo "Probando $NOMBRE en $IP..."
        PING_RESULT=$(ping -c 3 -W 1 "$IP" | tail -1 | awk -F'/' '{print $5}')
        if [ -z "$PING_RESULT" ]; then
            PING_RESULT="-1"
        fi
        PING_VALORES["$NOMBRE"]="$PING_RESULT"
        
        if [ "$PING_RESULT" == "-1" ]; then
            NUEVO_ESTADO="NO_RESPONDE"
            if [ "${ESTADO_SERVIDORES[$NOMBRE]}" = "OK" ]; then
                ULTIMA_CAIDA["$NOMBRE"]=$(date '+%d/%m/%Y %H:%M:%S')
            fi
        else
            NUEVO_ESTADO="OK"
            if [ "${ESTADO_SERVIDORES[$NOMBRE]}" = "NO_RESPONDE" ]; then
                ULTIMA_RECUPERACION["$NOMBRE"]=$(date '+%d/%m/%Y %H:%M:%S')
            fi
            if (( $(echo "$PING_RESULT > 10" | bc -l) )); then
                NUEVO_ESTADO="WARNING"
                ARGUMENTO="$NOMBRE:0"
                python3 send_mail.py "$ARGUMENTO" &
            fi
        fi
        
        if [ "$NUEVO_ESTADO" = "NO_RESPONDE" ]; then
            if [ -n "${ULTIMA_CAIDA[$NOMBRE]}" ] && [ -z "${ULTIMA_RECUPERACION[$NOMBRE]}" ]; then
                TIEMPO_ACUMULADO["$NOMBRE"]=$(( ${TIEMPO_ACUMULADO[$NOMBRE]:-0} + 1 ))
            fi
        fi
        
        ESTADO_SERVIDORES["$NOMBRE"]="$NUEVO_ESTADO"
        echo "$NOMBRE $NUEVO_ESTADO ${ULTIMA_CAIDA[$NOMBRE]:--} ${ULTIMA_RECUPERACION[$NOMBRE]:--} ${TIEMPO_ACUMULADO[$NOMBRE]:-0} ${PING_VALORES[$NOMBRE]}" >> "$STATUS_FILE"
    done
    
    sleep 10
done
