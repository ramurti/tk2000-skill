// Chama rotinas de um programa do TK2000 no 6502 do emulador, uma chamada por linha de entrada, e
// imprime o que elas deixaram nos registradores e na memória, com os ciclos que levaram. Use para
// testar as rotinas do próprio jogo contra uma referência (em JavaScript, Python...) sem conduzir o
// jogo por teclas.
//
//   call PROGRAM.bin LOAD_ADDRESS < cases.txt
//   cada linha: ENTRY [a:HH] [w:ADDR:HEXBYTES]... [r:ADDR:LEN]...      (todos os números em hex)
//               ENTRY: a rotina (do arquivo de rótulos do ld65: ld65 -Ln build/prog.lbl ...)
//               a:HH: o registrador A na entrada; w: memória escrita antes da chamada; r: lida depois
//   saída:      CYCLES A X Y P [uma string hex por r:, na ordem]
//
// Toda linha começa da mesma memória: o programa como carregado, todo o resto zero (o estado
// não vaza de um caso para o próximo). A ROM NÃO está presente: rotinas que chamam a ROM
// (COUT, HOME, o carregador da fita) não podem ser testadas aqui; use o executor sem janela (run.cpp)
// para elas. Compilação (o cc65 não é necessário, os fontes do emulador sim):
//   c++ -std=c++17 -O2 -w -I$EMU/src -I/opt/homebrew/include/SDL2 -include $EMU/src/pch.h \
//       tools/harness/call.cpp $EMU/src/{Bus,Cpu6502,Rom,Ram}.cpp -L/opt/homebrew/lib -lSDL2 \
//       -o build/call
#include "pch.h"
#include "Bus.h"
#define private public                  // (só ferramenta de teste: lê os registradores da CPU)
#include "Cpu6502.h"
#undef private
#include "Rom.h"
#include "Ram.h"
#include <iostream>
#include <sstream>
#include <vector>

struct SRamLayout { void* vtable; byte ram[0x10000]; };
CBus bus;
CCpu6502 cpu{ bus };
CRam ramDev{ bus };
byte* ram = reinterpret_cast<SRamLayout*>(&ramDev)->ram;
CRom rom{ bus, ram };

int main(int argc, char** argv) {
	if (argc < 3) {
		fprintf(stderr, "uso: call PROGRAM.bin LOAD_ADDRESS < cases\n");
		return 2;
	}
	FILE* f = fopen(argv[1], "rb");
	if (!f) { perror(argv[1]); return 1; }
	int load = (int)strtol(argv[2], nullptr, 16);
	static byte image[0x10000];
	fread(image + load, 1, 0x10000 - load, f);
	fclose(f);
	rom.read(0xC05B, 0);                        // RAM sob a ROM: o vetor de reset é nosso
	std::string line;
	while (std::getline(std::cin, line)) {
		if (line.empty()) continue;
		memcpy(ram, image, sizeof(image));
		std::istringstream in(line);
		std::string entryHex;
		in >> entryHex;
		word entry = (word)strtol(entryHex.c_str(), nullptr, 16);
		byte a = 0;
		std::vector<std::pair<int, int>> reads;
		for (std::string op; in >> op; ) {
			if (op[0] == 'a') { a = (byte)strtol(op.substr(2).c_str(), nullptr, 16); continue; }
			auto c1 = op.find(':', 2);
			int addr = (int)strtol(op.substr(2, c1 - 2).c_str(), nullptr, 16);
			std::string arg = op.substr(c1 + 1);
			if (op[0] == 'w') {
				for (size_t i = 0; i + 1 < arg.size(); i += 2) ram[addr + i / 2] = (byte)std::stoi(arg.substr(i, 2), nullptr, 16);
			} else {
				reads.push_back({ addr, atoi(arg.c_str()) });
			}
		}
		// at $0200: LDA #a / JSR entry / PHP / PLA / STA $02FE / LDA #1 / STA $02FF / JMP *
		// (os registradores são lidos depois do PHP/PLA: P é guardado em $02FE; A X Y como a rotina
		// os deixou são capturados parando logo depois que o JSR retorna)
		byte code[] = { 0xA9, a, 0x20, (byte)(entry & 0xFF), (byte)(entry >> 8),
			0x08, 0xEA, 0xA9, 0x01, 0x8D, 0xFF, 0x02, 0x4C, 0x0C, 0x02 };
		memcpy(ram + 0x200, code, sizeof(code));
		ram[0x2FF] = 0;
		ram[0xFFFC] = 0x00; ram[0xFFFD] = 0x02;
		cpu.reset();
		uint64_t start = cpu.getCumulativeCycles(), limit = start + 2000000000ULL;
		byte ra = 0, rx = 0, ry = 0;
		bool returned = false;
		while (!ram[0x2FF] && cpu.getCumulativeCycles() < limit) {
			if (!returned && cpu.mRegPC.value == 0x0205) {   // de volta do JSR: os registradores
				returned = true;
				ra = cpu.mRegA; rx = cpu.mRegX; ry = cpu.mRegY;
			}
			cpu.executeOpcode();
		}
		byte p = ram[0x0100 + (byte)(cpu.mRegS + 1)];          // o status empilhado pelo PHP
		printf("%llu %02X %02X %02X %02X", (unsigned long long)(cpu.getCumulativeCycles() - start), ra, rx, ry, p);
		for (auto& [addr, len] : reads) {
			printf(" ");
			for (int i = 0; i < len; i++) printf("%02X", ram[(addr + i) & 0xFFFF]);
		}
		printf("\n");
		fflush(stdout);
	}
	return 0;
}
