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
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)

---

**Container:** `speaker-verification`
**Ecossistema:** Mordomo
**Posição no Fluxo:** Terceiro — autenticação de usuário (GATE de autorização)

---

## 📋 Propósito

Valida se o falante é um usuário autorizado antes de liberar resultados downstream. É o **GATE de autorização** do pipeline de voz: somente após `mordomo.speaker.verified` o orchestrator processa a transcrição do Whisper e despacha ações.

**Otimização de Latência:** Enquanto a verificação ocorre (~200ms), o Whisper ASR e o Speaker ID/Diarization já começam a processar em paralelo. O orchestrator aguarda ambos antes de agir.

**IMPORTANTE:** Este componente **NÃO gerencia permissões**. Apenas identifica o usuário e confirma que a voz está cadastrada. A autorização (o que o usuário pode fazer) é responsabilidade do `mordomo-orchestrator` + `mordomo-vault`.

---

## 🔧 Tecnologias

**Linguagem:** Python 3.11

**Modelo:** [ECAPA-TDNN](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb) via ONNX Runtime
- Arquitetura: ECAPA-TDNN (Emphasized Channel Attention, Propagation and Aggregation)
- Treinado em: VoxCeleb1 + VoxCeleb2 (~1.2M utterances, 7000+ speakers)
- Embedding: **192D** (L2-normalizado)
- EER no VoxCeleb1-O: **~0.87%** (vs ~5-7% do GE2E/Resemblyzer anterior)
- Backend: ONNX Runtime CPU (exportado do SpeechBrain via multi-stage Docker build)
- Dockerfile multi-stage: Stage 1 exporta PyTorch→ONNX, Stage 2 roda apenas com onnxruntime (~2GB menor)

**Por que ECAPA-TDNN?**
É o estado da arte em speaker verification com ampla adoção em produção. O EER de 0.87% representa uma redução de ~6x no erro em relação ao Resemblyzer GE2E. Para um ambiente doméstico com 2 usuários conhecidos, a margem de segurança é muito alta.

**Framework:** asyncio + nats-py

---

## 📊 Especificações

```yaml
Input:
  Audio Duration: 1–3 segundos
  Sample Rate: 16000 Hz
  Format: PCM 16-bit mono (base64 no payload NATS)

Model:
  Architecture: ECAPA-TDNN
  Source: speechbrain/spkrec-ecapa-voxceleb (exportado para ONNX no build)
  Path: /app/model/ecapa_tdnn.onnx (embutido na imagem)

Verification:
  Threshold: 0.25 (cosine similarity — configurável via VERIFICATION_THRESHOLD)
  Embedding Dimension: 192D
  Scale: mesma speaker 0.30–0.80 / diferente -0.10–0.25

Performance (Orange Pi 5 Ultra, ARM64):
  RAM: ~400 MB (modelo carregado)
  Latency: < 300 ms por verificação (CPU)
  Accuracy (VoxCeleb1-O): EER ~0.87%
```

> ⚠️ **Threshold:** O valor padrão 0.25 é um ponto de partida conservador. Durante o enrollment/validação, monitore os logs (`confidence=X.XXX`) e ajuste via `VERIFICATION_THRESHOLD` — suba para reduzir falsos positivos, baixe para reduzir falsos negativos.

---

## 💾 Armazenamento de Embeddings

```
/data/embeddings/          ← bind mount (host → container, RW)
  ├── metadata.json        ← índice: speaker_id → { person_id, name, role, enrolled_at }
  ├── {speaker_id}.npy     ← embedding 192D ECAPA-TDNN (float32)
  └── ...
```

> ⚠️ **Re-enrollment obrigatório após upgrade do Resemblyzer:** Os embeddings antigos eram 256D (GE2E). Os novos são 192D (ECAPA-TDNN). Eles são **incompatíveis**. Apague todos os `.npy` e `metadata.json` existentes e re-enroll todos os speakers via `mordomo.speaker.enroll`.

---

## 🔄 Fluxo Paralelo com Gate

```
mordomo.audio.snippet
       │
       ├──→ [Speaker Verification]   ← este container
       ├──→ [Whisper ASR]            ← começa a processar em paralelo
       └──→ [Speaker ID/Diarization] ← começa a processar em paralelo

       ... processamento simultâneo ...

[✅ mordomo.speaker.verified] → orchestrator GATE ABRE → processa transcrição
[❌ mordomo.speaker.rejected] → orchestrator descarta tudo
```

---

## 🔌 Interfaces NATS

### Subscriptions (inbound)

| Subject | Descrição |
|---|---|
| `mordomo.audio.snippet` | Clip de áudio pós wake-word para verificar |
| `mordomo.speaker.enroll` | Enroll de novo speaker (apenas admin) |
| `mordomo.speaker.enroll.delete` | Remoção de speaker (apenas admin) |

### Publications (outbound)

| Subject | Descrição |
|---|---|
| `mordomo.speaker.verified` | Voz verificada — libera o pipeline |
| `mordomo.speaker.rejected` | Voz não reconhecida — bloqueia o pipeline |
| `mordomo.speaker.enrolled` | Confirmação de enrollment concluído |

### Payloads

**mordomo.audio.snippet** (inbound):
```json
{
  "audio_b64": "<base64 PCM 16-bit mono 16kHz>",
  "sample_rate": 16000
}
```

**mordomo.speaker.verified** (outbound):
```json
{
  "speaker_id": "renan-A1",
  "person_id": "<uuid>",
  "name": "Renan",
  "role": "admin",
  "confidence": 0.74
}
```

**mordomo.speaker.rejected** (outbound):
```json
{
  "speaker_id": null,
  "confidence": 0.18,
  "reason": "below_threshold"
}
```

**mordomo.speaker.enroll** (inbound):
```json
{
  "requester_speaker_id": "renan-A1",
  "name": "Ana",
  "role": "member",
  "audio_b64": "<base64 PCM>",
  "sample_rate": 16000,
  "person_id": "<uuid opcional>"
}
```

---

## 🔒 Setup Mode (Bootstrap)

O primeiro enrollment não pode exigir um admin pré-existente — bootstrap paradox. O container resolve assim:

- **`SETUP_MODE=false` (padrão/produção):** Enrollment via NATS só é aceito se o `requester_speaker_id` for um admin cadastrado. Se nenhum admin existe ainda, **um** enrollment é permitido automaticamente (bootstrap de uma vez).
- **`SETUP_MODE=true` (setup explícito):** Enrollment aberto, sem verificação de admin. O container loga um WARNING a cada 60s. **Remova após enrolar o admin.**

**Procedimento de setup inicial:**
1. Suba o container com `SETUP_MODE=true` em `docker-compose.override.yml`
2. Envie `mordomo.speaker.enroll` com `role=admin` para o seu speaker
3. Reinicie sem `SETUP_MODE=true`
4. A partir de agora, somente o admin pode enrolar novos speakers

---

## ⚙️ Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `NATS_URL` | `nats://nats:4222` | URL do NATS |
| `EMBEDDINGS_PATH` | `/data/embeddings` | Volume de embeddings |
| `MODEL_SAVEDIR` | `/app/model` | Diretório do modelo ONNX (ecapa_tdnn.onnx) |
| `VERIFICATION_THRESHOLD` | `0.25` | Threshold de cosine similarity |
| `SETUP_MODE` | `false` | Modo bootstrap de enrollment |

---

## 📁 Estrutura de Código

```
src/
  config.py     — variáveis de ambiente e subjects NATS
  verifier.py   — ECAPA-TDNN embed_audio() + verify()
  store.py      — persistência de embeddings (.npy) + metadata.json
  handlers.py   — handlers NATS: snippet, enroll, enroll_delete
  main.py       — entrypoint: carrega modelo, conecta NATS, subscriptions
```
