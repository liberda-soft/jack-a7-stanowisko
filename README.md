# Stanowisko JACK A7

Interaktywny model 3D stębnówki **JACK A7 (A7-DH)** z pomocą w diagnozowaniu problemów i doborze ustawień.

**Strona:** https://liberda-soft.github.io/jack-a7-stanowisko/

## Co jest w środku
- **Model 3D** maszyny i stołu (Three.js). Kliknij część, żeby zobaczyć opis i powiązane problemy.
- **Diagnoza:** 22 problemy z przyczynami ułożonymi od najbardziej prawdopodobnej i krokami naprawy do odhaczania.
- **Naprężenie:** symulator balansu nici górnej i dolnej (pętelki od spodu i od góry, nić widoczna po drugiej stronie).
- **Ustawienia:** igła, nić, ścieg, prędkość, docisk i tryb transportu dla 9 materiałów.
- **Nawlekanie:** krok po kroku, z nicią rysowaną na modelu.
- **Panel:** przyciski, parametry P i kody błędów Err.
- **Serwis:** harmonogram konserwacji i dane techniczne.

## Edycja
Dane są w `data/jack_a7_knowledge.json`, a szablon strony w `src/template.html`. Po zmianach przebuduj stronę:

```bash
python3 src/build.py data/jack_a7_knowledge.json index.html
```

Nieoficjalny pomocnik do własnej maszyny. Teksty oznaczone „(praktyka ogólna)” nie pochodzą z instrukcji JACK.
