# Flux – The Temporal Programming Language for Ex Nihilo OS

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/exnihilo/flux)
[![TVM](https://img.shields.io/badge/TVM-compatible-purple)](https://github.com/exnihilo/tvm)

> **"Every line of code is an intention. Every intention creates a world."**

Flux is the first **temporal-causal programming language**, designed exclusively for the *Ex Nihilo* operating system – a world without files, processes, or irreversible errors. Instead of classical execution, Flux programs express **intentions** that **become reality** across parallel **timelines**, with probabilities and paradoxes as first-class citizens.

---

## ✨ Why Flux?

- **No files, no processes** – just intentions and causal mosaics.
- **Mistakes are not errors** – they become parallel timelines you can explore or abandon.
- **Probabilities are persistent** – every value can exist in multiple states with different weights.
- **Paradoxes as security** – authentication through temporally impossible patterns.
- **Causal hardening** – make intervals of time truly irreversible (like `commit` for reality).

## 🚀 Quick Example

```flux
intentie HelloWorld {
    declansare: la_primul_semn_cognitiv()
    prioritate: 0.9
    executa: {
        trimite_senzatie("imagine mentală", 
            "✨ Welcome to a world without files! ✨", 
            3s);
        
        raspuns = asculta_intentie(utilizator, 10s, "silence");
        
        daca raspuns != "silence" : {
            colapseaza(raspuns, "pondere_maximă");
            trimite_senzatie("vorbire interioară", 
                "You said: " ++ raspuns, 
                1s);
        }
    }
}
This program doesn't "run" – it becomes real in the temporal consensus of Ex Nihilo.

📦 Installation
Flux requires Python 3.12+ for the compiler toolchain (the production TVM runs natively on Ex Nihilo hardware).

bash
git clone https://github.com/exnihilo/flux.git
cd flux
pip install -r requirements.txt
sudo make install   # installs fluxc and tvm
Verify installation:

bash
fluxc --version
tvm --version
🧠 Core Concepts
Concept	Description
Intention	An atomic unit of execution that triggers on an event, with priority and condition.
Timeline	A parallel causal branch. Every decision or mistake creates a new timeline.
Probability	A value between 0 and 1 representing existence weight across timelines.
Collapse	The act of turning a probabilistic expression into a concrete value.
Causal Mosaic	A file‑system without files – a sparse temporal matrix.
Causal Hardening	Making a time interval irreversible (expensive, requires consensus).
Paradox	A controlled logical inconsistency used for security or creativity.
📖 Language Guide
Basic Syntax
flux
# Comments start with '#'

x = 42 cu_probabilitate 0.85;   # x is 42 in 85% of timelines

durata = 10s;                   # time units: s, ms, ns, cycles

interval = [1s, 5s];            # closed temporal interval
Intentions
flux
intentie MyIntent {
    declansare: la fiecare 5s
    prioritate: 0.7
    conditie: vid_cauzal.exista()
    executa: {
        # ... actions
    }
}
Control Structures
flux
daca conditie : {
    # then branch
} altfel : {
    # else branch
}

pentru i in [1, 10] : {
    # loop over a collection
}

in_timp_ce conditie : {
    # use with care – may create paradoxes
}
Built‑in Functions
Function	Description
trimite_senzatie(tip, continut, durata?)	Send a cognitive sensation (image, inner voice, tactile)
asculta_intentie(sursa, timeout, fallback)	Listen for user/system intention
colapseaza(expr, metoda)	Collapse probability (pondere_maximă, medie, aleator)
creaza_timeline(din, pondere)	Fork a new timeline
inchegare_cauzala(interval, cost_maxim)	Make time interval irreversible
declanseaza_paradox(tip, interval)	Generate a controlled paradox
Causal Mosaic (Files without files)
flux
mozaic_cauzal user_data {
    componente: matrice_sparsa_temporala(),
    politici: { scriere: "adăugă_ramură", citire: "cea_mai_probabilă" }
}

# Write
user_data.acces(cheie: "last_thought").scrie("I forgot something", pondere=0.9);

# Read
memory = user_data.acces(cheie: "last_thought").citeste();
🛠️ Toolchain
Compiler fluxc
bash
fluxc program.flux                # compiles to program.fluxb
fluxc program.flux --dump-ast     # show abstract syntax tree
fluxc program.flux --dump-bytecode
fluxc program.flux --run          # compile and run on TVM
fluxc repl                        # interactive REPL
Temporal Virtual Machine tvm
bash
tvm program.fluxb --timeline main --prob-threshold 0.5
Debugger fluxdbg
bash
fluxdbg program.fluxb
Debugger commands:

timeline list – show all active timelines

switch <id> – change current timeline

colapseaza prob – force a probability collapse

rescrie [interval] – undo last actions (if not hardened)

📚 Full Documentation
User Manual – complete language reference

Ex Nihilo OS Book – design philosophy

API Reference – built‑ins and standard library

🧪 Examples
Check the examples/ directory:

Example	Description
hello.flux	Basic "Hello World" using cognitive sensations
probabilities.flux	Working with probabilistic values and collapse
mosaic.flux	Using the causal mosaic as persistent storage
paradox_security.flux	Authentication through temporal paradoxes
timeline_fork.flux	Creating and merging timelines
Run an example:

bash
fluxc examples/hello.flux --run
🧰 Requirements for Building from Source
Python 3.12+

antlr4 (optional, for grammar development)

Ex Nihilo hardware (for native execution) – or use the TVM emulator on Linux/macOS/Windows

🤝 Contributing
We welcome contributions! Flux is still a young language – there are many paradoxes waiting to be discovered.

Fork the repository

Create your feature branch (git checkout -b feature/amazing-paradox)

Commit your changes (git commit -m 'Add a new collapse method')

Push to the branch (git push origin feature/amazing-paradox)

Open a Pull Request

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

📄 License
Distributed under the MIT License. See LICENSE for more information.

🙏 Acknowledgements
The Ex Nihilo OS team – for building a world without files

Early adopters who weren't afraid to break causality

Every user who has ever said: "I wish I could undo that mistake"

📞 Contact & Community
Discord Server

Mailing List

GitHub Issues

Flux is not just a programming language – it's a way to reshape reality, one intention at a time.
Ex Nihilo, development team – anytime, never.
