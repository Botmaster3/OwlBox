# Audio-Fehlersuche: stufenweise Inbetriebnahme

Diese Anleitung ist für genau einen Fall gedacht: **der Ton knistert, knackt
oder rauscht während der Wiedergabe**, und es ist nicht klar, woran es liegt.

Sie ersetzt das Herumprobieren durch ein Verfahren, das die Ursache
garantiert einkreist: Es wird bei "nur Audio, sonst nichts" angefangen, und
dann wird **eine** Komponente nach der anderen zugeschaltet. Die erste Stufe,
bei der es knistert, benennt den Verursacher direkt.

## Warum nicht einfach raten

Ein knisterndes Audiosignal auf dieser Hardware kann mindestens vier völlig
verschiedene Ursachen haben, die sich gegenseitig verdecken:

| Ursache | Klingt wie | Zeigt sich in |
|---|---|---|
| Falsche `config.txt` (zweite Soundkarte aktiv) | verzerrt, komplett falsch | `aplay -l` |
| Unterspannung / Netzteil zu schwach | Aussetzer, Neustarts | `vcgencmd get_throttled` |
| Buffer-Underrun (CPU/Scheduling) | Stottern, Aussetzer | `dmesg`, ALSA-XRUN-Meldungen |
| Elektrische Einkopplung (GPIO/PWM/Schaltlast) | **Knistern wie ein Wackelkontakt** | **nirgends** - keine Logmeldung |

Der letzte Fall ist der heimtückische: Er erzeugt **keine** Fehlermeldung. Die
CPU ist im Leerlauf, `dmesg` ist sauber, ALSA meldet nichts - und trotzdem
knistert es. Softwareseitige Prioritäts- oder Performance-Änderungen bringen
dagegen nichts, weil das Problem gar nicht digital ist. Nur das stufenweise
Zuschalten findet so etwas.

## Die Stufen

Das Skript dafür ist `sudo owlbox-audio-stage <Stufe>`. Es schaltet die
jeweilige Komponente in `config.yaml` scharf, startet die betroffenen Dienste
neu und zeigt danach an, was gerade aktiv ist. Kommentare in der
`config.yaml` bleiben dabei erhalten.

| Stufe | Was zusätzlich läuft | Befehl |
|---|---|---|
| 0 | nichts - nur `mpv` im Terminal | `sudo owlbox-audio-stage 0` |
| 1 | OwlBox-App (Web/Player), **keine** Hardware | `sudo owlbox-audio-stage 1` |
| 2 | + Kiosk/Display (Chromium) | `sudo owlbox-audio-stage 2` |
| 3 | + Backlight-PWM (GPIO 13) | `sudo owlbox-audio-stage 3` |
| 4 | + Taster und Drehregler | `sudo owlbox-audio-stage 4` |
| 5 | + RFID-Leser (= Normalbetrieb) | `sudo owlbox-audio-stage 5` |

Nach jeder Stufe **1-2 Minuten Musik hören**. Sauber → nächste Stufe.
Knistert es → die zuletzt zugeschaltete Komponente ist die Ursache.

`sudo owlbox-audio-stage status` zeigt jederzeit den aktuellen Stand, ohne
etwas zu verändern. Stufe 5 stellt exakt die normale Konfiguration wieder her,
das Verfahren hinterlässt also keine Altlasten.

Wichtig: In den Stufen 1-4 ist `simulate` bewusst **nicht** gesetzt. Der
globale `simulate`-Schalter würde den echten Player durch einen Stub ersetzen
und damit den Ton ganz abschalten - für eine Audio-Fehlersuche wertlos.
Stattdessen hat jede Hardwarekomponente ihren eigenen Schalter
(`rfid.reader`, `gpio.enabled`, `gpio.backlight_pin`), und nur die werden
umgelegt.

## Wenn schon Stufe 0 knistert

Dann liegt es nicht an der OwlBox-Software. Der Reihe nach prüfen:

1. `aplay -l` - es darf **nur** die HiFiBerry-Karte auftauchen. Erscheinen
   dort noch `bcm2835 Headphones` oder `vc4hdmi`, stimmt die `config.txt`
   nicht (siehe `docs/hardware.md`, Abschnitt zur Soundkarte).
2. `vcgencmd get_throttled` - muss `throttled=0x0` liefern. Alles andere
   heißt: Netzteil zu schwach oder Überhitzung.
3. Lautsprecherklemmen und Stromversorgung des Amp2 nachziehen.
4. Testweise ein anderes Netzteil verwenden - Schaltnetzteile mit schlechter
   Siebung sind eine klassische Quelle für hörbares Knistern.

## Wenn es erst ab Stufe 3 knistert

Dann ist es die **Backlight-PWM**. Gegenprobe: Helligkeit auf 100 % stellen.
Bei 100 % Tastverhältnis schaltet die PWM nicht mehr, die Störung muss dann
verschwinden; bei ~50 % ist sie am stärksten. Ändert sich das Knistern mit der
Helligkeit, ist es eindeutig belegt.

Abhilfen, in dieser Reihenfolge:

- `gpio.backlight_pin: null` setzen. Das Display läuft dann auf voller
  Helligkeit, die Dimmung entfällt - aber der Ton ist sauber.
- Den Backlight-Treibertransistor mit einem RC-Glied entstören und die
  Masseführung von der Audioplatine trennen.

## Wenn es erst ab Stufe 5 knistert

Dann ist es der **RFID-Leser**. Der RC522 hängt an Software-SPI, d.h. die
GPIO-Pins werden aus Python heraus einzeln umgeschaltet - siehe
`owlbox/rfid/soft_spi.py`. Zwei Ansatzpunkte:

- `rfid.poll_interval` erhöhen (z.B. auf `0.5`). Weniger Abfragen pro Sekunde,
  dafür reagiert das Auflegen eines Chips träger.
- Den RC522 auf **echtes Hardware-SPI** (SPI0) umverdrahten. SPI0 ist seit dem
  Wechsel auf das DSI-Display frei; siehe `docs/hardware.md`. Das beseitigt das
  Bit-Banging vollständig, erfordert aber Umlöten.
