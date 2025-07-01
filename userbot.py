#!/usr/bin/env python3
"""
Bot de Telegram con Sistema de Triaje - Versión Cuenta de Usuario
================================================================
ADVERTENCIA: Usar una cuenta personal para automatización puede violar los TOS de Telegram.
Úsalo bajo tu propio riesgo y con moderación.

Este script actúa como un agente de triaje que:
1. Responde a usuarios que te escriben (máximo 1 ciclo por día)
2. Da una respuesta adicional cortés
3. Luego ignora al usuario por 24 horas
"""

import os
import asyncio
import random
from datetime import datetime
from dotenv import load_dotenv
import redis
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Cargar las variables de entorno
load_dotenv()

# Configuración desde variables de entorno
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')  # Tu número de teléfono
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')  # URL completa de Redis

# Parsear REDIS_URL si es necesario
if REDIS_URL.startswith('redis://'):
    # Extraer host y puerto de la URL
    import re
    match = re.match(r'redis://(?:.*@)?([^:]+):(\d+)', REDIS_URL)
    if match:
        REDIS_HOST = match.group(1)
        REDIS_PORT = int(match.group(2))
    else:
        REDIS_HOST = 'localhost'
        REDIS_PORT = 6379
else:
    # Si no es una URL, asumir que es solo el host
    REDIS_HOST = REDIS_URL
    REDIS_PORT = 6379

# Tiempos de expiración
TTL_CONVERSACION = 6 * 60 * 60  # 6 horas para el contador
TTL_BLOQUEO = 24 * 60 * 60      # 24 horas de bloqueo

# Inicializar Redis
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )
    redis_client.ping()
    print("✅ Conexión a Redis establecida")
except redis.ConnectionError:
    print("❌ Error: No se pudo conectar a Redis")
    print(f"   Intentando conectar a: {REDIS_HOST}:{REDIS_PORT}")
    exit(1)

# Crear el cliente de Telegram
# Usamos StringSession para no crear archivos .session
client = TelegramClient(StringSession(), API_ID, API_HASH)

# Mensajes automáticos
MENSAJE_SALUDO = "Hello there! I'm glad to see you!! 😊 listen I have something important to tell you"
MENSAJE_DESPEDIDA = "I have an exclusive offer for you! But it's only available for a limited time. If you're interested click the link to don't miss out! 🔗https://www.fanvue.com/nadiagarc?free_trial=2101c8c4-d510-4114-b415-a811021d7544 Let's chill and have fun 😉!"

# Variable global para almacenar tu propio ID
MI_USER_ID = None

@client.on(events.NewMessage(incoming=True))
async def manejador_mensajes(evento):
    """
    Maneja mensajes entrantes con sistema anti-spam
    """
    
    # Solo responder a chats privados
    if not evento.is_private:
        return
    
    # No responder a tus propios mensajes
    if evento.sender_id == MI_USER_ID:
        return
    
    user_id = evento.sender_id
    
    # Claves de Redis
    clave_contador = f"message_count:{user_id}"
    clave_bloqueo = f"blocked:{user_id}"
    clave_insistencia = f"insistence:{user_id}"
    
    try:
        # Verificar bloqueo
        if redis_client.exists(clave_bloqueo):
            # Usuario bloqueado - solo registrar insistencia
            insistencia = redis_client.get(clave_insistencia)
            veces = int(insistencia) if insistencia else 0
            redis_client.setex(clave_insistencia, TTL_BLOQUEO, veces + 1)
            
            ttl = redis_client.ttl(clave_bloqueo)
            horas = ttl // 3600
            minutos = (ttl % 3600) // 60
            
            # Obtener nombre del usuario
            sender = await evento.get_sender()
            nombre = sender.first_name or "Usuario"
            
            print(f"🚫 {nombre} (ID: {user_id}) bloqueado por {horas}h {minutos}m")
            print(f"   Ha insistido {veces + 1} veces")
            return
        
        # Obtener contador actual
        contador_actual = redis_client.get(clave_contador)
        contador = int(contador_actual) if contador_actual else 0
        
        # Obtener info del remitente
        sender = await evento.get_sender()
        nombre = sender.first_name or "Usuario"
        
        print(f"💬 Mensaje de {nombre} (ID: {user_id}) - Ciclo #{contador + 1}")
        
        if contador == 0:
            # Primer mensaje: Saludar
            print(f"⏳ Preparando respuesta para {nombre}...")
            
            # Mostrar "escribiendo..." durante unos segundos
            async with evento.client.action(evento.chat_id, 'typing'):
                # Esperar 8-12 segundos (aleatorio para más naturalidad)
                import random
                tiempo_espera = random.uniform(4, 8)
                await asyncio.sleep(tiempo_espera)
            
            # Enviar el mensaje
            await evento.reply(MENSAJE_SALUDO)
            print(f"👋 Saludé a {nombre} después de {tiempo_espera:.1f} segundos")
            
            # Incrementar contador
            redis_client.setex(clave_contador, TTL_CONVERSACION, 1)
            
        elif contador == 1:
            # Segundo mensaje: Despedirse y bloquear
            print(f"⏳ Preparando despedida para {nombre}...")
            
            # Mostrar "escribiendo..." con tiempo variable
            async with evento.client.action(evento.chat_id, 'typing'):
                import random
                tiempo_espera = random.uniform(6, 10)
                await asyncio.sleep(tiempo_espera)
            
            # Enviar despedida
            await evento.reply(MENSAJE_DESPEDIDA)
            print(f"👋 Me despedí de {nombre} después de {tiempo_espera:.1f} segundos")
            
            # Activar bloqueo
            redis_client.setex(clave_bloqueo, TTL_BLOQUEO, "1")
            redis_client.delete(clave_contador)
            redis_client.delete(clave_insistencia)
            
            print(f"🔒 {nombre} bloqueado por 24 horas")
            
    except Exception as e:
        print(f"❌ Error: {e}")

@client.on(events.NewMessage(outgoing=True, pattern='/stats'))
async def estadisticas(evento):
    """
    Comando para ver estadísticas
    """
    if not evento.is_private:
        return
    
    try:
        bloqueados = len(redis_client.keys("blocked:*"))
        claves_insistencia = redis_client.keys("insistence:*")
        
        total_ignorados = 0
        max_insistencia = 0
        mas_insistente = None
        
        for clave in claves_insistencia:
            user_id = int(clave.split(":")[1])
            veces = int(redis_client.get(clave) or 0)
            total_ignorados += veces
            
            if veces > max_insistencia:
                max_insistencia = veces
                mas_insistente = user_id
        
        # Obtener nombre del más insistente
        nombre_insistente = "Nadie"
        if mas_insistente:
            try:
                entity = await client.get_entity(mas_insistente)
                nombre_insistente = entity.first_name or f"ID: {mas_insistente}"
            except:
                nombre_insistente = f"ID: {mas_insistente}"
        
        stats = f"""📊 **Estadísticas del Sistema**

🚫 Usuarios bloqueados: {bloqueados}
💬 Mensajes ignorados: {total_ignorados}
🏆 Más insistente: {nombre_insistente}
📨 Sus mensajes: {max_insistencia}

_Actualizado: {datetime.now().strftime('%H:%M:%S')}_"""
        
        await evento.edit(stats)
        
    except Exception as e:
        await evento.edit(f"Error: {e}")

async def main():
    """
    Función principal
    """
    global MI_USER_ID
    
    print("🤖 Iniciando sistema de respuestas automáticas...")
    print("⚠️  ADVERTENCIA: El uso de automatización en cuentas personales")
    print("    puede resultar en restricciones o baneo de tu cuenta.")
    print("    Úsalo con moderación y bajo tu propio riesgo.\n")
    
    # Conectar con número de teléfono
    print(f"📱 Conectando con el número {PHONE_NUMBER}...")
    
    await client.start(phone=PHONE_NUMBER)
    
    # Obtener y guardar nuestro ID
    yo = await client.get_me()
    MI_USER_ID = yo.id
    
    print(f"✅ Conectado exitosamente!")
    print(f"👤 Cuenta: {yo.first_name} {yo.last_name or ''}")
    print(f"📱 Username: @{yo.username}" if yo.username else "📱 Sin username")
    print(f"🆔 Tu ID: {yo.id}")
    print("\n⏳ Sistema activo. Responderé automáticamente a mensajes privados.")
    print("💡 Envía /stats en cualquier chat privado para ver estadísticas\n")
    print("⏸️  Presiona Ctrl+C para detener\n")
    
    # Mantener ejecutándose
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Sistema detenido")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")