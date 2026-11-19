// Executor do TK2000 sem janela, para testes: carrega um .ct2 com LOADT, segura teclas, tira
// capturas de tela e despeja a memória, tudo em tempo emulado.
//
// run TAPE.ct2|DISK.dsk (boot com CALL 49408; tempos contados dali) [-t SECONDS] [-s TIME:FILE.ppm]... [-k TIME:DURATION:KEY]... [-m ADDR:LEN]...
//     [-a TIME:DURATION:FILE.wav] [-w TIME:ADDR:HEXBYTES]
//   tempos em segundos emulados contados a partir do Play; KEY = left right up down space return ctrl ou uma letra;
//   -a grava a saída de áudio do emulador (as amostras do CAudio, como o tocador SDL as recebe)
#include "pch.h"
#include "Bus.h"
#include "Cpu6502.h"
#include "Rom.h"
#include "Ram.h"
#include "Video.h"
#include "Audio.h"
#include "Keyboard.h"
#include "Tape.h"
#include "Disk.h"

// O CRam mantém a memória dele privada (friend CMachine); ela é o primeiro membro depois da vtable
struct SRamLayout { void* vtable; byte ram[0x10000]; };
static_assert(sizeof(CRam) == sizeof(SRamLayout), "CRam layout changed");

CBus bus;
CCpu6502 cpu{ bus };
CRam ramDev{ bus };
byte* ram = reinterpret_cast<SRamLayout*>(&ramDev)->ram;
CRom rom{ bus, ram };
CVideo video{ bus, ram };
CAudio audio{ bus, cpu };
CKeyboard kb{ bus };
CTape tape{ bus, cpu };
CDisk disk{ bus, rom };

static double now = 0;		// segundos emulados desde o Play

// a saída de áudio entre dois tempos, gravada como WAV (mono, 16 bits)
struct SWavRec : CObserver<sAudioMsg> {
	double from = -1, to = -1;
	std::string file;
	std::vector<int16_t> samples;
	void notify(sAudioMsg& m) override {
		if (from >= 0 && now >= from && now < to) {
			samples.insert(samples.end(), m.bufferPtr, m.bufferPtr + m.count);
		}
	}
	void write(int rate) {
		FILE* f = fopen(file.c_str(), "wb");
		uint32_t data = (uint32_t)samples.size() * 2, riff = 36 + data, fmt = 16, r = rate, br = rate * 2;
		uint16_t pcm = 1, ch = 1, align = 2, bits = 16;
		fwrite("RIFF", 1, 4, f); fwrite(&riff, 4, 1, f); fwrite("WAVEfmt ", 1, 8, f);
		fwrite(&fmt, 4, 1, f); fwrite(&pcm, 2, 1, f); fwrite(&ch, 2, 1, f); fwrite(&r, 4, 1, f);
		fwrite(&br, 4, 1, f); fwrite(&align, 2, 1, f); fwrite(&bits, 2, 1, f);
		fwrite("data", 1, 4, f); fwrite(&data, 4, 1, f);
		fwrite(samples.data(), 2, samples.size(), f);
		fclose(f);
	}
} wavRec;

static void run(double secs) {
	const uint64_t chunk = (uint64_t)(CPU_CLOCK * MS_TO_RUN / 1000.0);
	const uint64_t end = cpu.getCumulativeCycles() + (uint64_t)(secs * CPU_CLOCK);
	while (cpu.getCumulativeCycles() < end) {
		const uint64_t s = cpu.getCumulativeCycles();
		while (cpu.getCumulativeCycles() - s < chunk) {
			cpu.executeOpcode();
		}
		bus.updateAll(cpu.getCumulativeCycles());
	}
}

static void shot(const std::string& file) {
	SRGB* fb = video.getFrameBuffer();
	FILE* f = fopen(file.c_str(), "wb");
	fprintf(f, "P6 %d %d 255\n", VIDEOWIDTH, VIDEOHEIGHT);
	fwrite(fb, 3, VIDEOWIDTH * VIDEOHEIGHT, f);
	fclose(f);
}

static SDL_Keycode keyCode(const std::string& name) {
	if (name == "left") return SDLK_LEFT;
	if (name == "right") return SDLK_RIGHT;
	if (name == "up") return SDLK_UP;
	if (name == "down") return SDLK_DOWN;
	if (name == "space") return SDLK_SPACE;
	if (name == "return") return SDLK_RETURN;
	if (name == "fire") return SDLK_PERIOD;
	if (name == "ctrl") return SDLK_LCTRL;
	return (SDL_Keycode)tolower(name[0]);
}

static void key(SDL_Keycode code, bool down) {
	SDL_KeyboardEvent e{};
	e.keysym.sym = code;
	e.state = down ? SDL_PRESSED : SDL_RELEASED;
	kb.keyEvent(e);
}

static void dump(const std::vector<std::pair<int, int>>& mems) {
	for (auto& [addr, len] : mems) {
		printf("  [%04X]", addr);
		for (int i = 0; i < len; i++) {
			printf(" %02X", ram[(addr + i) & 0xFFFF]);
		}
		printf("\n");
	}
}

struct SEvent { double t; int kind; std::string arg; SDL_Keycode code; };	// kind: 0 captura, 1 tecla apertada, 2 tecla solta, 3 poke

int main(int argc, char** argv) {
	if (argc < 2) {
		fprintf(stderr, "uso: run TAPE.ct2 [-t SECONDS] [-s TIME:FILE.ppm] [-k TIME:DURATION:KEY] [-m ADDR:LEN]"
			" [-a TIME:DURATION:FILE.wav] [-w TIME:ADDR:HEXBYTES]\n");
		return 2;
	}
	double total = 30;
	std::vector<SEvent> events;
	std::vector<std::pair<int, int>> mems;
	for (int i = 2; i + 1 < argc; i += 2) {
		std::string opt = argv[i], val = argv[i + 1];
		if (opt == "-t") {
			total = atof(val.c_str());
		} else if (opt == "-s") {
			auto c = val.find(':');
			events.push_back({ atof(val.substr(0, c).c_str()), 0, val.substr(c + 1), 0 });
		} else if (opt == "-k") {
			auto c1 = val.find(':'), c2 = val.find(':', c1 + 1);
			double t = atof(val.substr(0, c1).c_str()), d = atof(val.substr(c1 + 1, c2 - c1 - 1).c_str());
			SDL_Keycode k = keyCode(val.substr(c2 + 1));
			events.push_back({ t, 1, "", k });
			events.push_back({ t + d, 2, "", k });
		} else if (opt == "-a") {
			auto c1 = val.find(':'), c2 = val.find(':', c1 + 1);
			wavRec.from = atof(val.substr(0, c1).c_str());
			wavRec.to = wavRec.from + atof(val.substr(c1 + 1, c2 - c1 - 1).c_str());
			wavRec.file = val.substr(c2 + 1);
			audio.attach(&wavRec);
		} else if (opt == "-w") {
			auto c = val.find(':');
			events.push_back({ atof(val.substr(0, c).c_str()), 3, val.substr(c + 1), 0 });
		} else if (opt == "-m") {
			auto c = val.find(':');
			mems.push_back({ (int)strtol(val.substr(0, c).c_str(), nullptr, 16), atoi(val.substr(c + 1).c_str()) });
		}
	}
	std::sort(events.begin(), events.end(), [](auto& a, auto& b) { return a.t < b.t; });

	bus.resetAll();
	cpu.reset();
	run(3.0);
	const std::string media = argv[1];
	const bool isDisk = media.size() > 4 && media.substr(media.size() - 4) == ".dsk";
	if (isDisk ? !disk.insert(argv[1]) : !tape.insertCt2(argv[1])) {
		fprintf(stderr, "não foi possível ler %s\n", argv[1]);
		return 1;
	}
	kb.typeText(isDisk ? "CALL 49408\n" : "LOADT\n");
	while (kb.isTyping()) {
		run(0.1);
	}
	if (!isDisk) {
		tape.play();
	}
	bool tapeEnded = isDisk;
	size_t next = 0;
	const double step = MS_TO_RUN / 1000.0;
	while (true) {
		while (next < events.size() && events[next].t <= now + 1e-9) {
			auto& e = events[next++];
			if (e.kind == 0) {
				shot(e.arg);
				printf("t=%.1f captura %s\n", now, e.arg.c_str());
				dump(mems);
			} else if (e.kind == 3) {			// ADDR:HEXBYTES escritos na RAM
				auto c = e.arg.find(':');
				int a = (int)strtol(e.arg.substr(0, c).c_str(), nullptr, 16);
				for (size_t k = c + 1; k + 1 < e.arg.size() + 1 && k + 2 <= e.arg.size(); k += 2) {
					ram[a++] = (byte)strtol(e.arg.substr(k, 2).c_str(), nullptr, 16);
				}
			} else {
				key(e.code, e.kind == 1);
			}
		}
		if (now >= total - 1e-9) {
			break;
		}
		run(step);
		now += step;
		if (!tapeEnded && !tape.getPlayState()) {
			tapeEnded = true;
			printf("t=%.1f fita parou\n", now);
		}
	}
	printf("t=%.1f fim\n", now);
	if (wavRec.from >= 0) {
		wavRec.write(audio.getSampleRate());
		printf("áudio: %zu amostras -> %s\n", wavRec.samples.size(), wavRec.file.c_str());
	}
	dump(mems);
	return 0;
}
