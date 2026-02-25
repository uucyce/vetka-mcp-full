pulse от Gemini


Ниже представлен детальный Backlog (список задач) и Архитектурный план для проекта "Pulse" (рабочее название).
Документ составлен на основе твоего стека (Tauri, Rust, MediaPipe, WebAudio) и отобранных библиотек (realtime-bpm-analyzer, essentia.js и т.д.). Я разбил работу на MVP (чтобы начать джемить как можно скорее) и последующие улучшения.
Pulse: Architecture and Implementation Roadmap
Status: Ready for dev
Project: Pulse (Tauri + React + Rust Audio/MIDI)
Target: macOS (Apple Silicon) / Windows
Stack: Tauri v2, React/TS, Rust (midir), MediaPipe, WebAudio
1. High-Level Architecture
Мы используем Hybrid Architecture:
Frontend (Main Brain): Весь DSP (синтез), анализ аудио (BPM/Key) и CV (Computer Vision) живут в Web-слое. Это дает минимальную задержку при визуализации и простоту разработки.
Backend (I/O Bridge): Rust используется для "тяжелого" системного I/O, который браузер делает плохо: стабильный MIDI I/O, низкоуровневые права доступа, файловая система (пресеты).
code
Mermaid
flowchart TD
    subgraph Frontend [Tauri Webview (React/TS)]
        UI[UI Layer: Controls & Visuals]
        
        subgraph Vision [Vision Pipeline]
            CAM[Camera Input] --> MP[MediaPipe Hands]
            MP --> GEST[Gesture Logic (Smoothing)]
        end
        
        subgraph AudioAnalysis [Listening Engine]
            MIC[Mic Input] --> RB[Ring Buffer (2-4s)]
            RB --> BPM[realtime-bpm-analyzer]
            RB --> KEY[Essentia.js / KeyFinder]
            BPM & KEY --> SYNC[Sync State (Tempo/Scale)]
        end
        
        subgraph Synthesis [Sound Engine]
            SYNC --> HARM[Harmony Engine (Camelot)]
            GEST --> HARM
            HARM --> WA[WebAudio Graph (Osc/FX)]
        end
    end

    subgraph Backend [Tauri Core (Rust)]
        R_MIDI[Midir (MIDI I/O)]
        R_SYS[System Commands]
    end

    UI <--> R_SYS
    HARM --"IPC (Events)"--> R_MIDI
    WA --> SPK[Speakers]
    R_MIDI --> EXT[External Synths]
2. MVP Backlog (Issue-Level)
Epic A: Foundations & Shell
Базовая настройка проекта и доступов.
PULSE-001: Bootstrap Tauri Project
Scope: Создать проект npm create tauri-app. Настроить TypeScript + React + Vite.
Libs: TailwindCSS (для UI), Lucide-react (иконы).
AC (Acceptance Criteria): Приложение запускается, показывает черный экран с хедером.
PULSE-002: Device Permissions Manager
Scope: Реализовать запрос прав на Камеру и Микрофон. MacOS очень капризен с этим.
Tech: navigator.mediaDevices.getUserMedia.
AC: При старте всплывают системные диалоги, потоки видео и аудио доступны в JS.
Epic B: Vision & Control (The "Hands")
Управление звуком через жесты.
PULSE-003: MediaPipe Hands Integration
Scope: Интегрировать @mediapipe/hands. Рендер видеопотока на canvas + оверлей точек рук.
Libs: @mediapipe/tasks-vision (новее и быстрее старого @mediapipe/hands).
AC: Видим скелет рук поверх видео с 30+ FPS.
PULSE-004: Gesture Mapping Engine
Scope: Преобразование координат в нормализованные данные (0.0 - 1.0).
Left Hand Y: Pitch (высота ноты).
Right Hand Pinch: Volume (громкость/Gate).
Right Hand X: Filter Cutoff / FX.
Algorithm: Добавить Smoothing (EMA - Exponential Moving Average), чтобы координаты не дрожали.
AC: Значения в консоли меняются плавно, без рывков.
Epic C: Synthesis & Harmony (The "Voice")
Генерация звука, который всегда попадает в ноты.
PULSE-005: Basic WebAudio Synth
Scope: Создать класс SynthEngine. 2 Осциллятора (Saw/Square) -> Filter -> VCA -> Reverb -> Limiter -> Output.
Libs: WebAudio API (native).
AC: При нажатии кнопки в UI слышен звук.
PULSE-006: Camelot & Scale Quantizer
Scope:
Реализовать структуру данных Camelot Wheel (1A..12A).
Функция quantize(input: float, scale: string) -> Frequency.
Маппинг "Left Hand Y" на ноты выбранной гаммы.
Libs: camelot-wheel-notation (или самописная логика массивов нот).
AC: Двигая рукой вверх-вниз, слышим только ноты выбранной тональности (например, C Minor).
Epic D: Listening & Analysis (The "Ear")
Анализ входящего аудио для подстройки.
PULSE-007: BPM Detection (Real-time)
Scope: Подключить микрофон к realtime-bpm-analyzer.
UI: Отображение текущего BPM. Кнопка "TAP" для коррекции.
AC: Включаем метроном на телефоне (120 BPM) -> приложение показывает ~120 BPM.
PULSE-008: Key Detection (Windowed)
Scope:
Кольцевой буфер (Ring Buffer) на 4 секунды аудио.
По кнопке "Listen" (или раз в 5 сек) запускать анализ через essentia.js.
Конвертация результата (напр. "C Major") в Camelot код ("8B").
Libs: essentia.js (Core Audio analysis).
AC: Играем аккорд C Major на гитаре/пиано -> приложение переключает скейл на 8B.
Epic E: Connectivity (The "Bridge")
Связь с внешним миром.
PULSE-009: Rust MIDI Output
Scope:
Rust: подключить крейт midir.
Tauri Command: send_midi_note(note, velocity).
Frontend: Отправлять MIDI события при смене ноты рукой.
AC: Ableton Live (или другой DAW) принимает ноты от приложения "Pulse".
3. Техническая реализация (Code Snippets)
A. Структура проекта
code
Text
src-tauri/
  src/
    main.rs       # Entry point
    midi.rs       # MIDI logic (midir)
src/
  components/     # React UI
  audio/
    engine.ts     # WebAudio Graph
    analysis.ts   # BPM & Key logic wrapper
  vision/
    tracker.ts    # MediaPipe logic
  music/
    theory.ts     # Camelot & Scales
B. Audio Analysis (Frontend TS)
Пример использования realtime-bpm-analyzer в связке с микрофоном:
code
TypeScript
// src/audio/analysis.ts
import { RealtimeBpmAnalyzer } from 'realtime-bpm-analyzer';

export class AudioListener {
  private audioCtx: AudioContext;
  private analyzer: RealtimeBpmAnalyzer;
  
  constructor() {
    this.audioCtx = new AudioContext();
    this.analyzer = new RealtimeBpmAnalyzer();
  }

  async startListening(onBpm: (bpm: number) => void) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const source = this.audioCtx.createMediaStreamSource(stream);
    
    // Подключаем анализатор
    source.connect(this.analyzer.analyzerNode);
    
    this.analyzer.subscribe((bpm) => {
      console.log('Detected BPM:', bpm);
      onBpm(bpm); // Обновляем UI или Синт
    });
  }
}
C. Harmony Logic (Quantizer)
Простая логика для квантования Y-координаты руки в ноту гаммы:
code
TypeScript
// src/music/theory.ts
const SCALES = {
  '8B': [60, 62, 64, 65, 67, 69, 71, 72], // C Major (MIDI notes)
  '5A': [60, 62, 63, 65, 67, 68, 70, 72], // C Minor
  // ... добавить остальные
};

export function quantizeCoordinate(y: number, scaleKey: string): number {
  // y приходит от 0.0 (верх) до 1.0 (низ)
  // Инвертируем, чтобы верх был высокой нотой
  const value = 1.0 - Math.min(Math.max(y, 0), 1); 
  
  const scale = SCALES[scaleKey] || SCALES['8B'];
  const index = Math.floor(value * scale.length);
  
  return scale[index]; // Возвращает MIDI ноту
}
D. Rust MIDI Bridge (Backend)
В src-tauri/src/main.rs (упрощенно):
code
Rust
use midir::{MidiOutput, MidiOutputConnection};
use std::sync::Mutex;
use tauri::State;

struct MidiState(Mutex<Option<MidiOutputConnection>>);

#[tauri::command]
fn init_midi(state: State<MidiState>) -> Result<String, String> {
    let midi_out = MidiOutput::new("Pulse_Midi_Out").map_err(|e| e.to_string())?;
    // Логика выбора порта (упрощено - берем первый)
    let ports = midi_out.ports();
    if let Some(port) = ports.first() {
        let conn = midi_out.connect(port, "pulse-conn").map_err(|e| e.to_string())?;
        *state.0.lock().unwrap() = Some(conn);
        return Ok("Connected".into());
    }
    Err("No MIDI ports found".into())
}

#[tauri::command]
fn send_note(state: State<MidiState>, note: u8, velocity: u8) {
    if let Some(conn) = state.0.lock().unwrap().as_mut() {
        // Note On channel 1
        let _ = conn.send(&[0x90, note, velocity]); 
    }
}

fn main() {
    tauri::Builder::default()
        .manage(MidiState(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![init_midi, send_note])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
4. Рекомендованный порядок разработки
День 1: Setup Tauri. Реализовать WebAudio синт (просто кнопку, которая гудит).
День 2: Подключить MediaPipe. Сделать так, чтобы Y-координата меняла частоту осциллятора (Theremin style).
День 3: Добавить "Brain". Реализовать маппинг нот (Scale Quantizer). Теперь это не Theremin, а музыкальный инструмент.
День 4: Подключить анализ аудио. Интегрировать realtime-bpm-analyzer. Вывести BPM на экран.
День 5: Интегрировать Rust MIDI. Попробовать управлять Ableton'ом с помощью жестов.
Это самый быстрый путь к работающему прототипу для джема!