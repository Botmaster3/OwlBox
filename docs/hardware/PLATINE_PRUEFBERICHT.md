# OwlBox v2 – Trägerplatine: Prüfbericht

**Stand:** 29.08.2026 · **Ergebnis: nicht fertigungsreif – nicht bestellen.**

Dieses Dokument ist der einzige erhaltene Stand der Platinen-Prüfung. Die
Entwurfsdateien selbst (`build_schematic.py`, `build_pcb.py`, die KiCad-Dateien,
die Gerber und die 2080-zeilige Entwicklungshistorie `LIESMICH.md`) lagen
ausschließlich im flüchtigen Arbeitsverzeichnis der Entwicklungssitzung und
wurden nie ins Repository übernommen. Beim Neuaufsetzen des Containers sind sie
verloren gegangen. Was hier steht, ist aus dem Sitzungsprotokoll rekonstruiert
und war zum Zeitpunkt der Messung belegt.

Wer den Entwurf neu aufbaut, sollte diesen Bericht vorher lesen – die meisten
Befunde sind Konstruktionsfehler, die beim Neuaufbau schlicht nicht wieder
gemacht werden sollten.

---

## Kurzfassung

Die Platine hatte drei voneinander unabhängige Problemschichten:

1. **Der Schaltplan** enthielt Fehler, die den Aufbau beim ersten Einschalten
   zerstört hätten (falsche Verstärker-Pinbelegung, fehlende Freilaufdiode,
   EN-Pin über dem Grenzwert).
2. **Das Layout** enthielt 91 echte Kupferkurzschlüsse zwischen verschiedenen
   Netzen.
3. **Die Prüfwerkzeuge** hatten blinde Flecken und meldeten deshalb „in
   Ordnung", wo es das nicht war. Das ist der eigentliche Grund, warum die
   Fehler so lange überlebt haben.

---

## Warum die Prüfung so lange nichts gefunden hat

Drei Werkzeugfehler, alle selbst verursacht, alle nachgewiesen:

**Kreuzungen waren strukturell unsichtbar.** Die Abstandsprüfung
(`final_verify.py`) berechnete den Abstand zweier Leiterbahnen als Minimum von
vier Endpunkt-zu-Strecke-Abständen. Bei zwei Bahnen, die sich *kreuzen*, sind
alle vier Werte positiv – die Kreuzung selbst wurde nie gemessen. Ein Router,
der gegen dieses Maß validiert wird, produziert zwangsläufig Kreuzungen.

> Nachbau-Hinweis: Der Test auf Streckenschnitt (Orientierungstest über
> Kreuzprodukte) muss in der Abstandsfunktion selbst stecken, nicht nur in der
> Rechteck-Variante.

**Verbindungen wurden nur über Koordinaten geprüft, nicht über Lagen.**
`completeness_check.py` verband Kupfer, wenn zwei Endpunkte dieselbe XY-Position
hatten – unabhängig von der Lage. Eine Bahn, die auf B.Cu exakt auf dem
Mittelpunkt eines reinen F.Cu-Pads endet, galt damit als angeschlossen. Sie ist
es nicht; dort fehlt ein Via.

Auswirkung auf die gemeldeten Zahlen:

| Layoutstand | XY-Prüfung (falsch) | lagenbewusst (richtig) |
|---|---|---|
| „99 Netze" | 99 | **83** |
| ausgeliefert | 105 | **93** |

**Die Massefläche fehlte in der Abstandsprüfung komplett.** Dadurch blieb
unbemerkt, dass 23 Vias fremder Netze mitten in der Massefläche lagen –
Kurzschlüsse gegen GND. Ursache: Nach dem Ergänzen von Vias wurde die Fläche
nie neu gefüllt, sodass die Freistellungen fehlten.

**Gegenprobe, die diese Diagnose stützt:** Trennt man das Kupfer nach Herkunft,
ist Freeroutings eigenes Ergebnis (587 Bahnen) **kurzschlussfrei**. Alle 91
Kreuzungen stammten aus eigenen Routing-Durchläufen; 88 davon zwischen zwei
0,2-mm-Bahnen.

---

## Blocker im Schaltplan

Diese wiegen am schwersten, weil kein Layout sie heilt.

### Verstärker TAS5756M: 16-Pin-Belegung auf einem 48-Pin-Gehäuse

Der Schaltplan wies dem Bauteil 16 Netze zu, das Gehäuse
(`TSSOP-48_6.1x12.5mm_P0.5mm`) hat 48 Pads – 32 blieben ohne Netz:

```
1:+PVDD  2:+PVDD  3:+3V3  4:GND  5:GND  6:I2C1_SDA  7:I2C1_SCL  8:GND
9:GND  10:I2S_BCLK  11:I2S_LRCLK  12:I2S_DIN
13:OUTA_P  14:OUTA_N  15:OUTB_P  16:OUTB_N
```

Das ist die Belegung eines generischen 16-Pin-Symbols. Nach Auswertung des
TI-Datenblatts liegt Pin 2 in Wahrheit auf einem Brückenausgang (SPK_OUTA−) und
Pin 4 auf dem anderen (SPK_OUTA+) – die Endstufe läge beim Einschalten fest
zwischen PVDD und Masse. Ebenfalls fehlend: Bootstrap-Kondensatoren,
GVDD_REG-Kondensator, AVDD/CPVDD/DVDD-Entkopplung, Reset-/PDN-Beschaltung.

> **Quellenlage ehrlich:** ti.com und alle Datenblattportale waren in der
> Prüfsitzung vom Netz-Proxy gesperrt. Die Einzelpins stammen aus zwei
> übereinstimmenden Suchmaschinen-Auswertungen. **Vor dem Neuaufbau das PDF
> selbst besorgen.** Der 16-gegen-48-Widerspruch steht unabhängig davon fest.

### Buck-Regler TPS54560: vier Fehler

| | im Entwurf | erforderlich |
|---|---|---|
| EN-Pin (U1-3) | `VIN_FUSED` = 12–24 V | max. **8,4 V** → Spannungsteiler VIN→EN→GND (zugleich UVLO) |
| Freilaufdiode an `SW_NODE` | **fehlt** – Netz hatte nur U1-8, L1-1, C_BOOT1-2 | Schottky ≥ 40 V, > 4 A (z. B. B540C, SS54) |
| Bootstrap-Kondensator | 10 nF | **100 nF** X7R ≥ 10 V |
| Eingangskondensator | 1 µF / 50 V / 1206 | ≥ 4,5 µF **wirksam bei 24 V**, plus 100 nF direkt am VIN-Pin |

Der TPS54560 ist ein **asynchroner** Abwärtswandler: High-Side-FET intern,
Freilaufdiode extern. Ohne sie gibt es keinen Strompfad in der Sperrphase – der
Regler arbeitet nicht und der Bootstrap-Kondensator wird nie nachgeladen.

Zum Eingangskondensator, eigene Rechnung ΔV = I·D·(1−D)/(C·f):

| Betriebspunkt | ΔV bei 1 µF nominal | mit DC-Bias-Derating (~0,6 µF) |
|---|---|---|
| 24 V / 3,3 A | 1,36 V | 2,27 V |
| 12 V / 3,3 A | 2,00 V | ~2,8 V |

Zielwert wäre ≤ 300 mV.

### CM5: nur 8 von 51 Masse-Pins verdrahtet

Verdrahtet waren 1, 2, 22, 32, 42, 52, 59, 98. Die fehlenden sind unter anderem
sämtliche GND-Pins des unteren Steckverbinders – also genau die Rückstrompfade
für PCIe, MIPI, USB 3.0 und Ethernet.

> Raspberry Pi Ltd, *Compute Module 5 Datasheet*, Abschnitt 4.2.1:
> „**Always connect all ground pins on any connector in use.**"

Auf der Platine hatten dadurch 111 von 204 CM5-Pads gar kein Netz.

### 3,3-V-Schiene um ein Vielfaches überlastet

Einzige Quelle waren die CM5-Pins 84/86. Laut Datenblatt (Tabelle 4) liefern
sie **300 mA je Pin, zusammen 600 mA**. Daran hingen 24 Anschlüsse, darunter
neun 3,3-V-Pins des M.2-Sockels für eine NVMe-SSD (1,5–3 A im Schreibbetrieb),
dazu Touchcontroller, RFID-Modul, zwei Encoder, Verstärker-DVDD, Mikrofon,
I²C-Pull-ups und LAN-LEDs.

**Richtig wäre:** eigener 3,3-V-Regler aus `+5V_LOGIC` (≥ 3 A) für M.2 und
Peripherie; CM5-Pins 84/86 nur noch als `GPIO_VREF`.

### Entkopplung praktisch nicht vorhanden

Der ganze Entwurf hatte zwölf Kondensatoren. Davon:

- `+3V3`: **null** – an einer Schiene mit SSD, Display und Verstärker-DVDD.
- `+5V_LOGIC`: nur zwei Elkos am Reglerausgang, **kein einziger Keramik**,
  insbesondere keiner an den sechs 5-V-Pins des CM5 (bis 2,5 A mit schnellen
  Lastsprüngen).
- `USBC_VBUS`: **null** – USB verlangt am Host-Port ≥ 10 µF, der Lastschalter
  braucht zusätzlich einen Ausgangskondensator zur Stabilität.

### Verpolschutz über dem Grenzwert

`D_RPP1` = BZT52C15 (15 V) klemmt V_GS des AO3401A (V_GS max **±12 V**):

- bei 24 V Eingang: −15 V → 25 % über dem Grenzwert
- bei 12 V Eingang: −12 V → exakt am Grenzwert, null Reserve

**Richtig wäre:** BZT52C10 (10 V), oder ein PMOS mit ±20 V V_GS (DMP3098L,
SI2323DS).

---

## Blocker im Layout

- **91 echte Kurzschlüsse** zwischen verschiedenen Netzen (gemessene
  Überlappung, Abstand 0,000 mm). Verteilung: F.Cu 28, In2.Cu 28, B.Cu 35.
  Besonders gefährlich: `+3V3` ↔ `+5V_LOGIC` (5×) und
  `+5V_LOGIC` ↔ `VIN_PROTECTED` (die rohen 12–24 V auf der 5-V-Schiene).
- **Der CM5 bekam keine 5 V.** Die sechs 5-V-Pins bildeten drei isolierte
  Zweier-Inseln (77/79, 81/83, 85/87), auf *jedem* Layoutstand. Die Platine
  hätte nicht gebootet.
- **Kein einziges Differenzpaar** hielt die geforderte Längengleichheit von
  0,15 mm (CM5-Datenblatt 4.2.2): CSI D1 lag 21,7 mm daneben (145-fach), PCIe
  REFCLK 12,5 mm (84-fach). Bei CSI D1 lagen P und N sogar auf verschiedenen
  Lagen. Der Median-Abstand innerhalb der Paare ging bis 11,6 mm – das sind
  keine Paare, sondern Einzelleitungen. Zusätzlich wechselte die Bahnbreite
  *innerhalb* einzelner Paare (0,10 / 0,15 / 0,20 mm).
- **Kein Lagenaufbau in der Datei**, also keine Impedanzkontrolle. Überschlag
  mit branchenüblichem 1,6-mm-Vierlagenaufbau: 125 Ω statt 100 Ω auf F.Cu,
  ~163 Ω auf In2.Cu (dort fehlt überhaupt eine benachbarte Massefläche).
- **130 Signalsegmente lagen auf der Massefläche In1.Cu**, darunter der
  Schaltknoten `SW_NODE` des Reglers über 66,7 mm – 24 V, 400 kHz, mehrere
  Ampere quer durch die Referenzlage.
- **Rückstrompfad an Lagenwechseln fehlte**: Signal-Vias der schnellen Paare
  lagen 8–15 mm vom nächsten Masse-Via entfernt (Richtwert ≤ 2 mm).
- **Massepads ohne Anschluss**: Die Stitching-Vias waren 0,02–0,5 mm *neben*
  den Pads platziert, ohne Verbindungsstück. GND hatte null Leiterbahnsegmente;
  48 von 57 SMD-Massepads hingen elektrisch in der Luft.

---

## Weiteres, das beim Neuaufbau zu beachten ist

- **Die Netzliste wurde nie in die Platine importiert.** `build_pcb.py` setzte
  die Netze selbst. Deshalb fiel niemandem auf, dass 247 Pads gar kein Netz
  hatten (CM5 111, M.2 36, Verstärker 32, USB-C 10, Regler 10,
  Befestigungslöcher 36, DSI 4, LAN 4). Solange dieser Schritt fehlt, kann kein
  Werkzeug einen Pin-Fehler finden. **Diesen Schritt beim Neuaufbau von Anfang
  an einbauen.**
- **Thermal Pad des Reglers ohne Netz** – der Wärmepfad des 5-A-Reglers endete
  im Nichts, die Thermovias führten nirgendwohin.
- **Kein ESD-Schutz** an irgendeinem nach außen führenden Stecker (USB-C,
  Hohlstecker, Taster, Encoder, RFID, UART, Lautsprecher, DSI). Bei einem
  Kindergerät keine Kosmetik.
- **Steckerschirme nicht angeschlossen**: USB-C (4 Pads), DSI (2), LAN (4),
  sowie alle 36 Pads der vier Befestigungslöcher.
- **`C_PVDD1` = 100 µF / 35 V im 1210 gibt es nicht.** Bei 35 V endet 1210 bei
  etwa 10 µF.
- **TPS2051B liefert 500 mA**, der Port wird über 56-kΩ-CC-Widerstände aber als
  900-mA-Port beworben.
- **5-V-Budget ohne Reserve**: CM5 2,5 A + Display 0,5 A + Lüfter 0,18 A +
  USB-C 0,9 A + Subwoofer 0,7 A ≈ 4,8 A bei einem 5-A-Regler. Mit dem zusätzlich
  nötigen 3,3-V-Regler reicht es nicht mehr.
- **`FB1`** (Ferritperle 0805) trug den gesamten Verstärkerstrom (~1,72 A
  Dauerstrom, Transienten darüber) ohne konkrete Typennummer.
- **Lüfter laufen nach dem Herunterfahren weiter** (CM5-Datenblatt 2.11) – über
  `VBUS_EN` mitschalten.
- **`FAN2_TACH` ohne Pull-up** (Open-Collector am GPIO ohne internen Pull-up).
- **Kein Anlaufstrombegrenzer** bei 430 µF am 24-V-Eingang.
- **Keine Stückliste** in der Lieferung; mehrere Bauteile ohne Bestellnummer
  (`PTC_4A`, `BLM21_600R`, `8.2uH_7A`, `22uH`, `AO3401A`, `BAT54`).
- **Fertigungsdaten passten zum ältesten Layoutstand.** Bohrdatei 423 Löcher =
  `delivery/OwlBox_v2.kicad_pcb` (423); der Arbeitsstand hatte 485, der
  aktuelle 522. Die beiliegende Zusicherung „gibt den aktuellen Stand wieder"
  war falsch.

---

## Was nachweislich in Ordnung war

Damit beim Neuaufbau nicht doppelt geprüft wird:

- **CM5-Pinbelegung: alle 98 belegten Pins fehlerfrei**, maschinell gegen
  Tabelle 4 des Datenblatts abgeglichen – 0 Abweichungen, 0 Doppelbelegungen.
  Das schließt die zwischen CM4 und CM5 geänderten Bereiche ein: 128–142 (nur
  die ungeraden MIPI0-Pins belegt, die geraden USB3-Pins korrekt frei), Pin 111
  = VBUS_EN, Pins 94/96 korrekt *nicht* verdrahtet. Das war die sauberste
  Stelle des Entwurfs.
- **DSI-Steckverbinder** (22 Pins) identisch mit `J5` der Raspberry-Pi-Referenz.
- **M.2-Key-M-Belegung** korrekt, Lane-Richtungen stimmen, Kerbe richtig
  ausgespart.
- **TPS54560-Pinnummerierung** korrekt (der Fehler lag in der Beschaltung).
- **Rückkopplungsteiler** 53,6 k / 10,2 k → 5,004 V. **Spulenrippel** 1,21 A
  = 37 %, unkritisch. **L1** mit 7 A Sättigung ausreichend.
- **Keine Courtyard-Kollisionen**, Umriss 128,2 × 97,1 mm konsistent.

### Widerlegte Verdachtsfälle

- **PCIe-/USB3-Koppelkondensatoren fehlen nicht.** Raspberry Pis eigene
  Trägerplatine `CM5IO` führt diese Signale ebenfalls direkt vom Modul zum
  M.2-Sockel; die Kondensatoren sitzen spezifikationsgemäß auf der SSD bzw.
  bereits im Modul.
- **Restring 0,000 mm** an sechs Bohrungen ist korrekt – es sind NPTH-Löcher.
- **Die Massefläche schließt die auf ihr liegenden Signale nicht kurz** – die
  Füllung stellt alle 130 Segmente korrekt frei (0 Überdeckungen gemessen).
  Das Schlitzproblem bleibt, ein Kurzschluss ist es nicht.
- **Kamera-Steckverbinder**: Die Annahme, J5 und J16 der Referenz hätten
  unvereinbare Pinbelegungen, ist falsch – sie sind strukturell identisch
  (nur DPHY0 statt DPHY1 und SCL0/SDA0 statt SCL1/SDA1). Ein echter
  FH12-22S-Steckverbinder wäre direkt ableitbar gewesen.

---

## Empfohlene Reihenfolge beim Neuaufbau

1. **Schaltplan zuerst** – Verstärker komplett neu mit echtem Datenblatt,
   Reglerbeschaltung, alle CM5-Masse-Pins, eigener 3,3-V-Regler,
   Entkopplungskonzept, Verpolschutz-Zener, ESD, Schirme.
2. **Netzliste in die Platine importieren**, statt Netze im Layout-Skript zu
   setzen.
3. **Lagenaufbau festlegen** und impedanzkontrolliert bestellen; Bahnbreite und
   Abstand der Differenzpaare daraus ableiten.
4. **Verlegen** mit einem Router, dessen Kollisionsprüfung echten
   Streckenschnitt kennt – und die Prüfwerkzeuge vorher an einem Fall mit
   bekannter Antwort verifizieren.
5. **KiCad-DRC in der GUI laufen lassen** – Lötstopp-Stege und Pastenschablone
   deckt kein selbstgeschriebenes Skript ab.
6. **Gerber erst danach exportieren** und die Bohrungszahl gegen die Platine
   gegenprüfen.
