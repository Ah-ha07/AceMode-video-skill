#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import {spawnSync} from "node:child_process";

const SPEAKER = "zh_male_dayi_saturn_bigtts";
const VOICE_NAME = "大壹 2.0";
const RESOURCE_ID = "seed-tts-2.0";
const SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/tts/submit";
const QUERY_URL = "https://openspeech.bytedance.com/api/v3/tts/query";

const parseArgs = (argv) => {
  const parsed = {};
  for (let index = 0; index < argv.length; index++) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      parsed[key] = true;
    } else {
      parsed[key] = value;
      index++;
    }
  }
  return parsed;
};

const args = parseArgs(process.argv.slice(2));
const inputPath = path.resolve(String(args.input ?? "script.txt"));
const outputPath = path.resolve(
  String(args.output ?? "audio/voiceover.wav"),
);
const manifestPath = path.resolve(
  String(args.manifest ?? "audio/tts-manifest.json"),
);
const segmentDir = path.resolve(
  String(args["segment-dir"] ?? path.join(path.dirname(outputPath), "segments")),
);
const speed = Number(args.speed ?? 1.08);
const postSpeed = Number(args["post-speed"] ?? 1);

if (!Number.isFinite(speed) || speed < 0.5 || speed > 2) {
  throw new Error("--speed must be between 0.5 and 2");
}
if (!Number.isFinite(postSpeed) || postSpeed < 0.5 || postSpeed > 1.15) {
  throw new Error("--post-speed must be between 0.5 and 1.15");
}

const readKeychain = (service) => {
  const result = spawnSync(
    "security",
    [
      "find-generic-password",
      "-a",
      process.env.USER ?? "",
      "-s",
      service,
      "-w",
    ],
    {encoding: "utf8"},
  );
  return result.status === 0 ? result.stdout.trim() : undefined;
};

const appId =
  process.env.VOLCANO_APP_ID ?? readKeychain("codex-volcano-app-id");
const accessToken =
  process.env.VOLCANO_ACCESS_TOKEN ??
  readKeychain("codex-volcano-access-token");
if (!appId || !accessToken) {
  throw new Error(
    "Set VOLCANO_APP_ID and VOLCANO_ACCESS_TOKEN, or store them in the codex-volcano macOS Keychain entries before synthesis",
  );
}
if (!fs.existsSync(inputPath)) {
  throw new Error(`Narration input not found: ${inputPath}`);
}

const paragraphs = fs
  .readFileSync(inputPath, "utf8")
  .split(/\r?\n/)
  .map((line) => line.trim())
  .filter(Boolean);
if (paragraphs.length === 0) {
  throw new Error(`Narration input is empty: ${inputPath}`);
}

fs.mkdirSync(segmentDir, {recursive: true});
fs.mkdirSync(path.dirname(outputPath), {recursive: true});
fs.mkdirSync(path.dirname(manifestPath), {recursive: true});

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const hash = (value) =>
  crypto.createHash("sha256").update(value).digest("hex").slice(0, 16);

const headers = () => ({
  "Content-Type": "application/json",
  "X-Api-App-Id": appId,
  "X-Api-Access-Key": accessToken,
  "X-Api-Resource-Id": RESOURCE_ID,
  "X-Api-Request-Id": `editorial-tts-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
});

const fetchWithRetry = async (url, options, attempts = 3) => {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      return await fetch(url, options);
    } catch (error) {
      lastError = error;
      if (attempt < attempts) await sleep(attempt * 800);
    }
  }
  throw lastError;
};

const probeDuration = (filePath) => {
  const result = spawnSync(
    "ffprobe",
    [
      "-v",
      "error",
      "-show_entries",
      "format=duration",
      "-of",
      "default=nw=1:nk=1",
      filePath,
    ],
    {encoding: "utf8"},
  );
  if (result.status !== 0) {
    throw new Error(`ffprobe failed for ${filePath}: ${result.stderr}`);
  }
  const duration = Number(result.stdout.trim());
  if (!Number.isFinite(duration) || duration <= 0) {
    throw new Error(`Invalid duration for ${filePath}`);
  }
  return duration;
};

const synthesizeParagraph = async (text, index) => {
  const number = String(index + 1).padStart(2, "0");
  const textHash = hash(`${SPEAKER}|${speed}|${text}`);
  const audioPath = path.join(segmentDir, `segment-${number}-${textHash}.mp3`);
  const metadataPath = path.join(
    segmentDir,
    `segment-${number}-${textHash}.json`,
  );

  if (fs.existsSync(audioPath) && fs.existsSync(metadataPath)) {
    const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
    return {
      ...metadata,
      audioPath,
      duration: probeDuration(audioPath),
      reused: true,
    };
  }

  const requestHeaders = headers();
  const submitResponse = await fetchWithRetry(SUBMIT_URL, {
    method: "POST",
    headers: requestHeaders,
    body: JSON.stringify({
      user: {uid: "editorial-documentary-video"},
      req_params: {
        text,
        speaker: SPEAKER,
        audio_params: {
          format: "mp3",
          sample_rate: 24000,
          speech_rate: Math.round((speed - 1) * 100),
          enable_timestamp: true,
        },
      },
    }),
  });
  const submit = await submitResponse.json();
  if (!submitResponse.ok || submit.code !== 20000000) {
    throw new Error(
      `Volcengine submit failed for segment ${number}: ${submit.message ?? submit.code}`,
    );
  }
  const taskId = submit.data?.task_id;
  if (!taskId) {
    throw new Error(`Volcengine returned no task_id for segment ${number}`);
  }

  let query;
  const startedAt = Date.now();
  while (Date.now() - startedAt < 90_000) {
    try {
      const response = await fetchWithRetry(QUERY_URL, {
        method: "POST",
        headers: requestHeaders,
        body: JSON.stringify({task_id: taskId}),
      });
      query = await response.json();
    } catch {
      await sleep(1000);
      continue;
    }
    if (query.data?.task_status === 2) break;
    if (query.data?.task_status === 3) {
      throw new Error(
        `Volcengine task failed for segment ${number}: ${query.message ?? "unknown"}`,
      );
    }
    await sleep(1000);
  }
  if (query?.data?.task_status !== 2 || !query.data?.audio_url) {
    throw new Error(`Volcengine timed out for segment ${number}`);
  }

  const audioResponse = await fetchWithRetry(query.data.audio_url, {}, 3);
  if (!audioResponse.ok) {
    throw new Error(
      `Volcengine audio download failed for segment ${number}: HTTP ${audioResponse.status}`,
    );
  }
  fs.writeFileSync(
    audioPath,
    new Uint8Array(await audioResponse.arrayBuffer()),
  );

  const metadata = {
    index,
    text,
    textHash,
    provider: "volcano",
    model: RESOURCE_ID,
    voiceName: VOICE_NAME,
    voiceId: SPEAKER,
    speed,
    sentences: query.data.sentences ?? [],
    audioPath,
    reused: false,
  };
  fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
  return {...metadata, duration: probeDuration(audioPath)};
};

const segments = [];
for (let index = 0; index < paragraphs.length; index++) {
  const segment = await synthesizeParagraph(paragraphs[index], index);
  segments.push(segment);
  console.log(
    `${segment.reused ? "REUSE" : "SUCCESS"} ${String(index + 1).padStart(2, "0")} ${segment.duration.toFixed(2)}s`,
  );
}

const concatPath = path.join(segmentDir, "concat.txt");
fs.writeFileSync(
  concatPath,
  `${segments
    .map((segment) => `file '${path.basename(segment.audioPath)}'`)
    .join("\n")}\n`,
);

const outputExtension = path.extname(outputPath).toLowerCase();
const audioCodecArgs =
  outputExtension === ".wav"
    ? ["-c:a", "pcm_s16le"]
    : ["-b:a", "192k"];
const masteringFilters = [
  postSpeed === 1 ? null : `atempo=${postSpeed}`,
  "acompressor=threshold=-20dB:ratio=3:attack=5:release=200:makeup=5dB",
  "loudnorm=I=-16:TP=-1.5:LRA=7",
].filter(Boolean);
const filter = masteringFilters.join(",");
const render = spawnSync(
  "ffmpeg",
  [
    "-hide_banner",
    "-loglevel",
    "error",
    "-f",
    "concat",
    "-safe",
    "0",
    "-i",
    concatPath,
    "-af",
    filter,
    "-ar",
    "48000",
    "-ac",
    "1",
    ...audioCodecArgs,
    "-y",
    outputPath,
  ],
  {cwd: segmentDir, encoding: "utf8"},
);
if (render.status !== 0) {
  throw new Error(`ffmpeg mastering failed: ${render.stderr}`);
}

let cursor = 0;
const timedSegments = segments.map((segment) => {
  const sourceStart = cursor;
  const start = sourceStart / postSpeed;
  const duration = segment.duration / postSpeed;
  const end = start + duration;
  cursor += segment.duration;
  const sentences = segment.sentences.map((sentence) => ({
    ...sentence,
    startTime: (sourceStart + sentence.startTime) / postSpeed,
    endTime: (sourceStart + sentence.endTime) / postSpeed,
    words: (sentence.words ?? []).map((word) => ({
      ...word,
      startTime: (sourceStart + word.startTime) / postSpeed,
      endTime: (sourceStart + word.endTime) / postSpeed,
    })),
  }));
  return {
    index: segment.index,
    text: segment.text,
    textHash: segment.textHash,
    audioPath: segment.audioPath,
    sourceDuration: segment.duration,
    start,
    end,
    sentences,
    reused: segment.reused,
  };
});

const finalDuration = probeDuration(outputPath);
fs.writeFileSync(
  manifestPath,
  JSON.stringify(
    {
      provider: "volcano",
      api: "V3 async TTS",
      model: RESOURCE_ID,
      voiceName: VOICE_NAME,
      voiceId: SPEAKER,
      language: "zh-CN",
      speed,
      postSpeed,
      outputPath,
      outputSampleRate: 48000,
      targetIntegratedLufs: -16,
      truePeakCeilingDbtp: -1.5,
      masteringFilters,
      duration: finalDuration,
      segments: timedSegments,
      generatedAt: new Date().toISOString(),
    },
    null,
    2,
  ),
);

console.log(`OUTPUT ${outputPath}`);
console.log(`MANIFEST ${manifestPath}`);
console.log(`DURATION ${finalDuration.toFixed(3)}s`);
