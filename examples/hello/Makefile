# make: build/hello.ct2 (uma fita que se executa sozinha: no emulador, insira-a, digite LOADT, Enter, F6)
# make run: um teste no emulador sem janela, com capturas de tela (precisa do código do emulador em EMU)
# EMU: a pasta src do código-fonte do emulador (emulador-tk2000/src)
EMU      ?= $(HOME)/tk2000/emulador-tk2000/src
SDL_INC  ?= /opt/homebrew/include/SDL2
SDL_LIB  ?= /opt/homebrew/lib
TOOLS     = ../../plugin/skills/tk2000-port/scripts/tk2000

build/hello.ct2: build/hello.bin $(TOOLS)/mkct2.py
	python3 $(TOOLS)/mkct2.py build/hello.bin 0x4000 0x4000 HELLO $@

build/hello.bin: hello.s tk2000.cfg | build
	ca65 -o build/hello.o -l build/hello.lst hello.s
	ld65 -C tk2000.cfg -m build/hello.map -Ln build/hello.lbl -o $@ build/hello.o

build/run: $(TOOLS)/harness/run.cpp | build
	c++ -std=c++17 -O2 -w -I$(EMU) -I$(SDL_INC) -include $(EMU)/pch.h $< \
		$(addprefix $(EMU)/,Bus.cpp Cpu6502.cpp Rom.cpp Ram.cpp Video.cpp Audio.cpp Keyboard.cpp Tape.cpp) \
		-L$(SDL_LIB) -lSDL2 -o $@

# o carregamento leva alguns segundos emulados; depois espaço, depois segura a seta para a direita por 1 s
run: build/hello.ct2 build/run
	build/run build/hello.ct2 -t 16 -s 8:build/text.ppm -k 9:0.1:space -k 11:1:right -s 15:build/game.ppm

build:
	mkdir -p build

.PHONY: run
