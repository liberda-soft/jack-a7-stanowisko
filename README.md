# JACK A7

Interaktywny model 3D stębnówki **JACK A7 (A7-DH)** z pomocą w diagnozowaniu problemów i doborze ustawień.

**Strona:** https://liberda-soft.github.io/jack-a7-stanowisko/

## Co jest w środku
- **Model 3D 1:1** maszyny i stołu (`jack_a7.glb`, Three.js). Kliknij część, żeby zobaczyć opis i powiązane problemy. Widok „Jak na zdjęciu” patrzy z tego samego miejsca co zdjęcie maszyny.
- **Diagnoza:** 22 problemy z przyczynami ułożonymi od najbardziej prawdopodobnej i krokami naprawy do odhaczania.
- **Naprężenie:** symulator balansu nici górnej i dolnej (pętelki od spodu i od góry, nić widoczna po drugiej stronie).
- **Ustawienia:** igła, nić, ścieg, prędkość, docisk i tryb transportu dla 9 materiałów.
- **Nawlekanie:** krok po kroku, z nicią rysowaną na modelu.
- **Panel:** przyciski, parametry P i kody błędów Err.
- **Serwis:** harmonogram konserwacji i dane techniczne.

## Jak powstał model 1:1
Wymiary nie są szacowane na oko, tylko zmierzone ze zdjęć tej konkretnej maszyny:
1. **Kalibracja aparatu:** kreski miarki 0–100 cm na blacie i obrys łoża (517 × 178 mm) dały pozycję i ogniskową aparatu dla każdego zdjęcia. Średni błąd to 1,4 px.
2. **Triangulacja:** narożniki panelu, nakrętki, korki, płytki ściegowe itd. zmierzono z dwóch zdjęć. Pozostałe punkty rzutowano na zmierzone płaszczyzny czoła ramienia (z = −15,7 cm) i obudowy kolumny (z = −12,7 cm).
3. **Kontrola z danymi JACK:** wyniki zgadzają się z broszurą (przestrzeń szycia 262 × 130 mm, wysokość ramienia ok. 22,5 cm) i ze standardem stołu (wycięcie 110 mm od przedniej krawędzi).
4. **Budowa:** model zbudowano w Blenderze (`model/build.py`). Panel i naklejka to wyprostowane fragmenty zdjęcia.
5. **Sprawdzenie:** render z tej samej kamery nałożono na zdjęcie (`model/overlay_photo3.png`, czerwone krawędzie = model).

Układ współrzędnych: cm, początek w lewym przednim narożniku blatu, x w prawo, y w górę, z do operatora.

Przebudowa modelu (Blender 4.2+):
```bash
blender -b --factory-startup -P model/build.py -- model/out render
```

## Edycja
Dane są w `data/jack_a7_knowledge.json`, a szablon strony w `src/template.html`. Po zmianach przebuduj stronę:

```bash
python3 src/build.py data/jack_a7_knowledge.json index.html
```

Nieoficjalny pomocnik do własnej maszyny. Teksty oznaczone „(praktyka ogólna)” nie pochodzą z instrukcji JACK.
