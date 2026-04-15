# 🔐 Speaker Verification

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---

**Container:** `speaker-verification`  
**Ecossistema:** Mordomo  
**Posição no Fluxo:** Terceiro - autenticação de usuário (GATE de autorização)

---

## 📋 Propósito

Valida se o falante é um usuário autorizado (você ou sua esposa) antes de liberar resultados downstream. **GATE de autorização** que controla o fluxo paralelo: Whisper ASR, Speaker ID e outros componentes começam a processar simultaneamente, mas só publicam resultados após receber `speaker.verified`.

**Otimização de Latência:** Processamento paralelo reduz tempo total em ~200-300ms, pois enquanto a verificação ocorre (200ms), os outros componentes já estão processando.

---

## 🎯 Responsabilidades

- ✅ **Identificar QUEM é o falante** (autenticação)
- ✅ Comparar embedding de voz com vozes cadastradas
- ✅ Aceitar apenas usuários autorizados (voz conhecida)
- ✅ Rejeitar vozes desconhecidas
- ✅ Atualizar embeddings ao longo do tempo (drift adaptation)

**IMPORTANTE:** Este componente **NÃO gerencia permissões**. Apenas identifica o usuário e valida se a voz está cadastrada. A autorização (O QUE o usuário pode fazer) é responsabilidade do **Conversation Manager** via sistema de níveis.

---

## 💾 Armazenamento de Embeddings

### Volume Compartilhado (Docker)

```yaml
# Estrutura de diretórios

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
./data/embeddings/  (host - persistência local)
  └─ /data/embeddings/  (container - bind mount RW)

Arquivos:
  ├─ user_1.npy      (você - admin)
  ├─ user_2.npy      (esposa)
  ├─ guest_*.npy     (convidados temporários)
  └─ metadata.json  (opcional - info adicional)
```

**Formato:** NumPy array (`.npy`)
- Dimensão: 256D (Resemblyzer)
- Latência de leitura: ~0.5-2ms (cache do kernel)
- Compartilhado com: Speaker ID/Diarization (read-only)

**Docker Compose:**
```yaml
services:
  speaker-verification:
    volumes:
      - ./data/embeddings:/data/embeddings:rw  # Read-Write
    environment:
      - EMBEDDINGS_PATH=/data/embeddings
```

**Vantagens:**
- ✅ Latência mínima (~1ms após cache)
- ✅ Zero overhead de rede
- ✅ Cache automático do kernel Linux
- ✅ Backup trivial (copiar pasta)
- ✅ Fácil inspeção/debug

---

## 🔧 Tecnologias

**Linguagem:** Python (obrigatório - ecossistema ML)

**Principal:** Resemblyzer
- Cria embeddings de voz (128D ou 256D)
- Similaridade cosine
- Backend: **PyTorch** (C++ libtorch)
- Leve e eficiente

**Alternativas:**
- pyannote.audio Speaker Embedding (PyTorch)
- SpeechBrain Speaker Recognition (PyTorch)
- Custom model (TensorFlow Lite)

**Performance:** Inference em C++ (libtorch), NumPy cosine similarity em C (OpenBLAS). Python overhead ~5ms.

---

## 📊 Especificações

```yaml
Input:
  Audio Duration: 1-3 segundos
  Sample Rate: 16000 Hz
  Format: PCM 16-bit mono

Verification:
  Threshold: 0.75 (cosine similarity)
  Enrolled Users: 2 (você + esposa)
  Embedding Dimension: 256
  
Performance:
  CPU: < 10% spike (inference)
  RAM: ~ 100 MB
  Latency: < 200 ms
  Accuracy: > 95%
```

---

## 🔄 Fluxo Paralelo com Gate

```
wake_word.detected
       ↓
       ├──→ [Speaker Verification] (200ms)
       ├──→ [Whisper ASR] (começa a processar)
       ├──→ [Speaker ID/Diarization] (começa a processar)
       └──→ [Source Separation] (standby)
       
       ... processamento paralelo ...
       
[✅ speaker.verified] ← GATE ABRE
       ↓
   Todos liberam resultados:
   ├─ Whisper → publica transcrições
   ├─ Speaker ID → envia contexto
   └─ Conversation Manager → recebe dados

[❌ speaker.rejected] ← GATE FECHA
       ↓
   Todo processamento descartado
   (desperdício: ~200ms CPU)
```

**Trade-off:** 5-10% das conversas são rejeitadas (desperdício), mas 90%+ ganham 200-300ms de latência.

**Reset do Gate:**
```
conversation.ended
       ↓
   [GATE RESETA]
       ↓
   Todos os componentes voltam ao estado IDLE:
   ├─ Whisper ASR → para consumo VAD, limpa buffer
   ├─ Speaker ID → descarta contexto, aguarda próximo
   ├─ Wake Word → volta a IDLE (detecta novamente)
   └─ Verification → pronto para próxima verificação
```

---

## 🔌 Interfaces

### Input
```python
# NATS Subscription

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
subject: "wake_word.detected"
payload: {
  "audio_snippet": "<base64 1s audio>",
  "timestamp": 1732723200.123
}
```

### Output
```python
# NATS Event - Authorized (voz conhecida)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
subject: "speaker.verified"
payload: {
  "user_id": "user_1",  # Identificação do usuário
  "confidence": 0.82,
  "timestamp": 1732723200.123
}
# Conversation Manager usa user_id para:

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
#  - Buscar nível de permissão (level)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
#  - Validar se pode executar ação solicitada

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
#  - Manter contexto individualizado

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---

# NATS Event - Unauthorized (voz desconhecida)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
subject: "speaker.rejected"
payload: {
  "reason": "unknown_voice",
  "similarity": 0.45,
  "timestamp": 1732723200.123
}
# Pipeline interrompido - nenhuma ação executada

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
```

---

## ⚙️ Configuração

```yaml
verification:
  threshold: 0.75
  min_audio_duration: 1.0  # segundos
  max_audio_duration: 3.0
  
users:
  # Usuários permanentes
  - id: "user_1"
    name: "Você (Admin)"
    embedding_path: "/data/embeddings/user_1.npy"
    # Nível de permissão gerenciado no Conversation Manager
    
  - id: "user_2"
    name: "Esposa"
    embedding_path: "/data/embeddings/user_2.npy"
    
  # Convidados temporários (opcional - cadastro rápido)
  - id: "guest_temp_abc123"
    name: "João (visitante)"
    embedding_path: "/data/embeddings/guest_temp_abc123.npy"
    # Auto-removido após expiração no Conversation Manager

drift_adaptation:
  enabled: true
  update_threshold: 0.85  # Atualiza se muito similar
  max_updates_per_day: 10

nats:
  url: "nats://nats:4222"
  subscribe: "wake_word.detected"
  publish_verified: "speaker.verified"
  publish_rejected: "speaker.rejected"
```

---

## 📈 Métricas

```python
speaker_verifications_total{user_id}
speaker_rejections_total{reason}
speaker_verification_latency_seconds
speaker_confidence_score
speaker_embedding_updates_total{user_id}
```

---

## 🔒 Segurança

### Enrollment (Cadastro inicial)
```bash
# Script para cadastrar vozes

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
python scripts/enroll_speaker.py \
  --user-id user_1 \
  --name "Você" \
  --audio-samples /data/samples/user_1/*.wav \
  --embeddings-path /data/embeddings
  
# Gera embedding médio de múltiplas amostras

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
# Salva em /data/embeddings/user_1.npy (volume compartilhado)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
# Speaker ID/Diarization lê automaticamente

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
```

**Processo:**
1. Gravar 10-20 amostras de voz (frases variadas, 3-5s cada)
2. Script processa todas e gera embedding médio
3. Salva `.npy` no volume compartilhado
4. Ambos serviços (Verification + Diarization) carregam automaticamente

**Hot Reload:**
- Novos embeddings detectados automaticamente (watchdog)
- Não precisa reiniciar containers

### Anti-Spoofing
```yaml
anti_spoofing:
  enabled: true
  check_liveness: true  # Detecta gravações
  min_variation: 0.05   # Variação mínima entre frames
```

---

## 🐳 Docker

```dockerfile
FROM python:3.11-slim

RUN pip install resemblyzer numpy nats-py watchdog

WORKDIR /app
COPY src/ ./src/
COPY scripts/ ./scripts/

# Volume para embeddings compartilhados

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-speaker-verification**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
VOLUME /data/embeddings

EXPOSE 8001

CMD ["python", "src/main.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  speaker-verification:
    build: ./speaker-verification
    container_name: speaker-verification
    volumes:
      - ./data/embeddings:/data/embeddings:rw  # Read-Write (cria/atualiza)
    environment:
      - EMBEDDINGS_PATH=/data/embeddings
      - NATS_URL=nats://nats:4222
      - THRESHOLD=0.75
    depends_on:
      - nats
    networks:
      - mordomo-network

volumes:
  embeddings_data:  # Volume nomeado (opcional)
    driver: local

networks:
  mordomo-network:
    driver: bridge
```

---

## 🔗 Integração

**Recebe de:** Wake Word Detector (NATS)  
**Envia para:** STT / Core API (NATS - speaker.verified)  
**Monitora:** Prometheus, Loki

---

## 🔐 Vault Integration

O `speaker.verified` publicado por este módulo é o **fator biométrico de autorização** consumido pelo `mordomo-vault`.

```yaml
Publica:
  speaker.verified:
    person_id: "renan"      # ID resolvido via mordomo-people
    confidence: 0.97        # usado pelo vault para checar min_confidence da política
    timestamp: ...

  speaker.rejected:
    reason: "unknown_voice"
```

O `mordomo-orchestrator` mantém `{ person_id, confidence }` na sessão ativa. Quando o orchestrator precisa despachar uma ação sensível (ex: PIX), encaminha esses valores para `mordomo.vault.secret.get`.

**Este módulo não acessa o vault diretamente** — apenas fornece o dado biométrico que o vault vai consumir.

Veja: [mordomo-vault](https://github.com/AslamSys/mordomo-vault)

---

**Versão:** 1.0
