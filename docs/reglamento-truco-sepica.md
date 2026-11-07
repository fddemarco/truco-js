# Reglamento oficial de juego — Se Pica Truco Series Argentina (TSA)

> **Fuente:** `reglamento-truco.pdf` (impresión de https://sepica.com.ar/reglamento) · Última actualización: 4 de noviembre de 2026 · Versión Edición 2026
> **Extracción:** capítulos 1–20 y Anexo A por OCR del PDF, revisados contra el texto de la web; Anexos B.2, B.3 y C tomados del texto completo de la web.

---

## 0. Resumen para implementación

### 0.1 Parámetros del juego

| Parámetro | Valor | Ref. |
|---|---|---|
| Jugadores por equipo | 3 (+1 suplente opcional, no puede entrar en medio del partido salvo fuerza mayor) | 1.2, 3.1, 4.4 |
| Equipos por partido | 2, sentados alternadamente | 1.2, 3.5 |
| Puntos para ganar | 30 (15 malas + 15 buenas) | 1.3, 1.4 |
| Tope del marcador | 30 (el excedente se descarta) | 1.5 |
| Formato | Partido único | 1.3 |
| Flor | **No se juega** | 1.6 |
| Mazo | Baraja española de 40 cartas (sin 8, 9 ni comodines) | 5.1 |
| Cartas por jugador | 3 | 5.5 |
| Sentido de juego/reparto | Hacia la **derecha** | 5.5, 5.7, 7.1 |
| Inicio del pica-pica | Mano siguiente a la que algún equipo alcance o supere **5** puntos | 15.1 |
| Fin del pica-pica | Cuando algún equipo alcanza o supera **25** puntos | 15.1 |
| Falta envido en pica-pica | 6 puntos fijos | 11.9, 15.8 |
| Penalidad por 2.º error de reparto (en el ciclo) | +2 puntos al rival y la mano se anula | 6.4 |
| Advertencias disciplinarias para perder el partido | 2 en el mismo partido | 19.2 |
| Tolerancia de presentación | 5 min → advertencia; 10 min → derrota por ausencia | 4.1 |
| Ventana de corrección administrativa | 15 min después de homologar | 16.8 |

### 0.2 Modelo de datos sugerido (entidades)

- **Torneo / Edición** → Fases → Grupos / Cuadro (definido por las *Condiciones Particulares*, 1.8).
- **Equipo**: nombre, jugadores (3 + suplente opcional), capitán por partido.
- **Partido**: equipos A/B, numeración reservada 1-2-3 de cada equipo, asientos, marcador, advertencias por equipo, estado (`programado`, `en_juego`, `finalizado`, `homologado`), tipo de resultado (deportivo o administrativo).
- **Mano**: tipo (`redonda` | `pica_pica`), repartidor, jugador mano, rondas, cantos, puntos adjudicados.
- **Duelo** (solo pica-pica): jugadores N vs N, rondas, cantos, puntos.
- **Contador de errores de reparto** por repartidor (ciclo de 2, se reinicia en cada partido).

### 0.3 Tipos de resultado

| Tipo | Cuándo | Registro |
|---|---|---|
| Deportivo | Un equipo llega a 30 | Marcador real (p. ej. 30–22) |
| Victoria por Ausencia | El rival no se presenta a los 10 min (4.1) | Administrativo, **no** 30–0 |
| Victoria por Descalificación | El rival es descalificado | Administrativo |
| Victoria por Abandono | El rival se niega a seguir o no puede (sin fuerza mayor autorizada) | Administrativo |
| Victoria por Sanción | El rival pierde por sanción sin ser descalificado (p. ej. 2.ª advertencia) | Administrativo |
| Doble Descalificación | Ambos descalificados en el mismo partido | Sin ganador; ninguno suma victoria |

Para la tabla de posiciones, una victoria administrativa vale **30 puntos a favor**, y su diferencia de puntos es el **promedio de diferencia** de las victorias que el beneficiado jugó de verdad en la misma fase (o 0 si no tiene ninguna) (1.13).

### 0.4 Desempate en grupos (1.13), en este orden

1. Mayor cantidad de partidos ganados.
2. Mejor diferencia de puntos (suma de puntos obtenidos − recibidos, partido a partido).
3. Mayor suma de puntos obtenidos.
4. Enfrentamiento directo (si los empatados jugaron entre sí y eso resuelve la igualdad).
5. Sorteo de Se Pica TSA.

Los mismos criterios ordenan a los segundos de grupo entre sí, si las Condiciones Particulares los clasifican.

---

## 1. Disposiciones generales y formato de competencia

- **1.1 Objeto.** Reglas de juego, conducta, arbitraje y registro de resultados de los partidos de Se Pica TSA. Forma parte del contrato junto con los Términos y Condiciones, las Condiciones Particulares de cada edición y la Política de Privacidad (Organizador: Brand Flow S.A.S.). En temas ajenos al juego, arbitraje o disciplina prevalecen los TyC y las Condiciones Particulares.
- **1.2 Modalidad.** Dos equipos de tres jugadores; seis jugadores sentados alternadamente.
- **1.3 Partido único.** A 30 puntos; gana el primero en llegar.
- **1.4 Malas y buenas.** Puntos 1–15 = malas; 16–30 = buenas.
- **1.5 Tope del marcador.** El resultado se detiene en 30; si una jugada daría más, solo se suman los puntos necesarios hasta 30.
- **1.6 Sin flor.** Con tres cartas del mismo palo se usan solo dos para el envido.
- **1.7 Mismas reglas** para partidos televisados, grabados y no televisados (las cámaras solo cambian las pruebas disponibles).
- **1.8 Cuadro y fases.** Las Condiciones Particulares de cada edición definen grupos, cuadro, fases, cupos por instancia y equipos invitados. La clasificación y los resultados administrativos se rigen por 1.13 y 1.14.
- **1.9 Naturaleza.** El resultado depende solo del desempeño deportivo; el Organizador no gestiona apuestas.
- **1.10 Inscripción.** Retribuye la organización; no es apuesta ni financia premios.
- **1.11 Premios.** Fijos, definidos antes de abrir inscripciones y financiados por el Organizador.
- **1.12 Prohibición de apuestas** para jugadores, capitanes, cuerpo técnico y familiares directos. Es una falta de integridad (cap. 18) y puede llevar a la descalificación (cap. 19).
- **1.13 Criterios de clasificación.** Ver §0.4.
- **1.14 Resultados administrativos.** Ver §0.3. Los partidos anteriores de un equipo descalificado quedan firmes.

## 2. Terminología oficial

| Término | Definición |
|---|---|
| **Ronda** | Instancia en la que cada jugador activo juega una carta en orden. (No se usa "baza".) |
| **Mano** | Conjunto de hasta 3 rondas, hasta que queda definido el ganador y los puntos. |
| **Ser mano** | Jugador ubicado inmediatamente a la derecha del mazo; inicia la primera ronda. |
| **Ser pie** | Último jugador en actuar dentro del orden. |
| **Mano redonda** | Mano en la que juegan los jugadores activos de ambos equipos en el orden general. |
| **Pica-pica** | Mano compuesta por 3 duelos individuales sucesivos entre jugadores con el mismo número. |
| **Duelo de pica-pica** | Enfrentamiento 1 vs 1 dentro de una mano de pica-pica. |
| **Jugador activo** | Puede jugar, cantar, responder, hacer señas y decidir en la mano o duelo. |
| **Tapar** | Poner las cartas boca abajo en la zona de tirada y dejar de participar en la mano (cartas identificables). |
| **Irse al mazo** | Abandonar la mano/duelo incorporando las cartas al mazo, o con la expresión reglamentaria válida. |
| **Partido** | Juego completo a 30 puntos. |
| **Capitán** | Representante formal del equipo ante la organización y el árbitro. |
| **Advertencia verbal** | Llamado de atención por una falta leve. No es sanción ni cambia el marcador. |
| **Advertencia disciplinaria** | Sanción que se computa al equipo. |
| **Canto fuera de turno** | Canto de un jugador activo al que no le toca jugar la próxima carta. |
| **Canto irregular** | Retruco o vale cuatro sin respetar la secuencia o cantado por un equipo sin derecho a subir. |

## 3. Equipos, capitán, numeración y ubicación

- **3.1 Integración.** 3 jugadores por partido; se puede inscribir un 4.º como suplente. La formación solo cambia entre partidos (cláusula XI de los TyC). No hay cambios tácticos una vez empezado el partido. Si la sede no admite más de 3 por equipo, el suplente no juega esa fase.
- **3.2 Capitán.** Uno por partido; solo se cambia entre partidos. Conserva su rol aunque tape o se vaya al mazo (puede reclamar, pero no hacer acciones de juego). Si sale por fuerza mayor, el árbitro puede autorizar un nuevo capitán.
- **3.3 Funciones del capitán.**
  - Confirmar la formación y la numeración reservada 1-2-3.
  - Ser el único que pide formalmente la intervención del árbitro.
  - Recibir y comunicar las decisiones arbitrales.
  - Ser el portavoz de las decisiones colectivas (su decisión obliga al equipo; no afecta las acciones individuales de juego ni las decisiones de los duelos).
  - Decidir si se continúa o se repite el reparto cuando se expone una carta destinada a su equipo (6.1).
  - Validar o impugnar el resultado en el sistema oficial.
- **3.4 Numeración reservada.** Antes del partido, cada equipo asigna en secreto los números 1, 2 y 3 y los comunica al árbitro. Queda fija todo el partido. El pica-pica siempre enfrenta 1 vs 1, 2 vs 2 y 3 vs 3. Un intento deliberado de alterar los cruces → advertencia verbal o disciplinaria; el fraude se rige por el cap. 19.
- **3.5 Ubicación.** Alternada, con los jugadores del mismo número **enfrentados**. Fija todo el partido. Alterarla deliberadamente → advertencia disciplinaria; reincidir después de una corrección del árbitro → posible descalificación.

## 4. Presentación, pausas y dispositivos

- **4.1 Presentación.** Los 3 jugadores habilitados deben estar listos a la hora oficial. A los **+5 min** → posible advertencia disciplinaria por demora. A los **+10 min** → pérdida por ausencia. El árbitro (o el Jefe de Árbitros) puede dejarlo sin efecto si hay demora de la organización, fuerza mayor o causa excepcional.
- **4.2 Dispositivos.** No se permiten celulares personales sobre la mesa ni auriculares, salvo los dispositivos autorizados para cargar el puntaje (solo para eso, con notificaciones silenciadas). El smartwatch se puede usar como reloj, pero no para leer mensajes; recibir una notificación no es infracción, abrirla sí. Negarse a retirar el celular o reincidir → advertencia disciplinaria. Está prohibido acceder a sitios de apuestas.
- **4.3 Levantarse de la mesa.** Requiere autorización del árbitro; salvo emergencia, no durante una mano. Sin justificación → advertencia disciplinaria. En las pausas no se usan dispositivos (salvo excepción autorizada) ni se recibe información del juego.
- **4.4 Fuerza mayor.** El árbitro puede suspender el juego. Con fuerza mayor comprobada, puede autorizar el ingreso del suplente registrado en el **mismo número y posición** (nunca para reemplazar a un descalificado ni como cambio táctico). Si impide resolver la mano en curso, puede anularla sin adjudicar puntos.

## 5. Mazo, barajado, corte y reparto

- **5.1 Mazo oficial.** Baraja española de 40 cartas, oficial o autorizada. No se permiten cartas propias.
- **5.2 Primer repartidor.** Cada jugador saca una carta al azar; reparte quien saque la de **mayor jerarquía de truco** (Anexo A). Si hay empate en el máximo, solo los empatados vuelven a sacar. Las cartas se devuelven al mazo antes de barajar.
- **5.3 Barajado.** Mezclar lo suficiente; se prohíbe marcar, doblar, retener o acomodar cartas.
- **5.4 Corte obligatorio.** Lo hace el **rival inmediato a la izquierda** del repartidor, antes de cada reparto. Puede hacerse sobre la mesa (modalidad de referencia, que el cortador puede exigir) o en la mano del repartidor. Debe dividir el mazo en 2 partes de **más de 3 cartas cada una**. No vale cortar en varios montones ni solo golpear el mazo. Negarse deliberadamente a lo que indique el árbitro → advertencia disciplinaria.
- **5.5 Reparto.** 3 cartas a cada jugador, **de a una**, empezando por el jugador a la **derecha** del repartidor y siguiendo hacia la derecha. Cada repartidor elige sacar de **arriba o de abajo** del mazo; esa modalidad queda fija desde su primer reparto del partido (aunque se repita) y para todos sus repartos siguientes. Usar la modalidad contraria = error de reparto (se repite el reparto, o se aplica 6.4 si es su 2.º error). Al terminar, el mazo queda a la derecha del repartidor (eso indica quién es mano).
- **5.6 No tocar durante el reparto.** Nadie toca sus cartas hasta que el repartidor entrega la 3.ª carta al último jugador; desde ahí todos pueden mirarlas (también en pica-pica, aunque su duelo no haya empezado). Si se expone una carta destinada al rival, nadie mira sus cartas hasta resolver según 6.1.
- **5.7 Rotación.** Al terminar cada mano, reparte el jugador a la **derecha** del repartidor anterior (salvo que una regla especial indique repetir).
- **5.8 Mazo defectuoso.** Antes de la mano: se reemplaza o corrige. Durante la mano, si pudo afectar el juego: el árbitro puede anular la mano; las manos anteriores quedan firmes salvo manipulación deliberada.

## 6. Errores e irregularidades del reparto

- **6.1 Errores del repartidor** (entre otros): exponer una carta destinada a un **rival**, dar cartas de más o de menos, saltear a un jugador, dejar cartas sin poder saber de quién son, cambiar la modalidad arriba/abajo, alterar el reparto. Exponer una carta **propia o de un compañero no es error** y el reparto sigue.
  - Si se expone una carta destinada al rival: se detiene el reparto y se registra el error. Si es el **1.º error del ciclo**, el capitán del equipo afectado decide si **continuar** (la carta expuesta sigue siendo de su destinatario) o **repetir** (el mismo repartidor baraja, ofrece el corte y reparte). En ambos casos el error **queda registrado**. Si alguien mira sus cartas antes de esa decisión, no se puede continuar con ese reparto (6.7/6.8).
  - Cada nueva carta rival expuesta suma otro error, aunque sea en el mismo reparto. Al llegar al **2.º error del ciclo** se aplica 6.4 de inmediato, aunque el primer error haya sido de otra clase.
  - Distintas irregularidades en el mismo reparto pueden contar como errores separados.
- **6.2 Desorden corregible.** Si se puede saber con certeza de quién es cada carta y ambos capitanes están de acuerdo, se reacomodan y se sigue. Cuenta como error, salvo que se convalide como irregularidad menor (6.9).
- **6.3 Desorden no corregible.** El reparto queda sin efecto, se computa el error y se reparte de nuevo.
- **6.4 Ciclo de errores del repartidor.**
  - **1.º error** → se registra; si hay que repetir, reparte de nuevo **el mismo** jugador.
  - **2.º error** del mismo repartidor en el ciclo → **+2 puntos al rival**, la **mano se anula** y el mazo pasa al **siguiente repartidor**. Se aplica aunque los dos errores sean del mismo reparto o el rival haya aceptado continuar.
  - Después de aplicarlo, el contador de ese repartidor vuelve a 0 y empieza un nuevo ciclo. Los contadores son **individuales por repartidor** y se reinician en cada partido.
- **6.5 Cantidad incorrecta de cartas.** Hay que avisar apenas se note y antes de cualquier acción para sacar ventaja; no se corrige descartando ni tomando cartas. Si se descubre durante la mano y fue de buena fe: la mano se anula, cuenta como error del repartidor y se reparte de nuevo, sin sanción al jugador. Una mano ya cerrada no se reabre (salvo indicios posteriores de ocultamiento).
- **6.6 Ocultamiento deliberado** de una cantidad incorrecta para sacar ventaja → su equipo **pierde el partido**. Una 2.ª vez en el torneo clasificatorio → **descalificación** (sin importar qué jugador lo hizo).
- **6.7 Manipulación indebida durante el reparto** (tocar o mirar antes de tiempo, mirar mientras está pendiente la decisión de 6.1, mirar cartas ajenas). Si es accidental y corregible, se restablece sin sanción (puede haber advertencia verbal). Si provoca desorden o expone cartas, el reparto puede anularse y la responsabilidad es del manipulador, no del repartidor.
- **6.8 Reiteración.** Reincidir después de una advertencia verbal → posible advertencia disciplinaria. **No** hay contador técnico individual ni +2 por estas conductas. Si es deliberado o fraudulento → sanción directa. El régimen de 6.4 es independiente.
- **6.9 Convalidación de irregularidades menores accidentales.** Pueden convalidarse por acuerdo de ambos equipos (en mano redonda deciden los capitanes; en un duelo de pica-pica, los dos contendientes). Si se sigue jugando a sabiendas, la irregularidad queda convalidada y no se puede reclamar después.
  - **No convalidables:** fraude, carteo, colusión, asistencia externa deliberada, cartas marcadas, manipulación intencional del mazo, agresiones, amenazas, seguridad, integridad.
  - **Siempre se registran y acumulan** (aunque haya acuerdo): la exposición de cartas destinadas al rival y el cambio de modalidad arriba/abajo.
  - La convalidación por accidente no impide revisar después si aparecen pruebas de que fue deliberado.

## 7. Desarrollo de la mano y de las rondas

- **7.1** El jugador mano juega primero; luego se sigue hacia la **derecha**.
- **7.2** Gana la ronda la carta de mayor jerarquía (Anexo A). Quien la gana empieza la ronda siguiente.
- **7.3 Empate entre compañeros.** Si dos o más jugadores del **mismo equipo** empatan con la carta más alta, la ronda es de su equipo; empieza la siguiente el que jugó primero entre ellos.
- **7.4 Ganador inactivo.** Si quien debería empezar ya no está activo, empieza el jugador inmediatamente a su derecha (sea del equipo que sea).
- **7.5** Las rondas ya terminadas conservan su resultado aunque un jugador quede inactivo después.
- **7.6 Pardas** (empate entre cartas de equipos rivales):

| Ronda 1 | Ronda 2 | Ronda 3 | Gana la mano |
|---|---|---|---|
| Parda | Gana X | — | X |
| Parda | Parda | Gana X | X |
| Parda | Parda | Parda | El equipo del jugador **mano** |
| Gana X | Parda | — | X |
| Gana X | Gana Y | Parda | X (el que ganó la 1.ª) |
| Gana X | Gana Y | Gana Z | Z |
| Gana X | Gana X | — | X |

  Después de una ronda parda, la ronda siguiente la empieza el jugador **mano** de esa mano.
- **7.7 Cartas jugadas.** Quedan boca arriba y separadas hasta el final de la mano, para poder reconstruir el orden. Manipularlas deliberadamente → advertencia verbal, y disciplinaria si se repite; ocultar información → 19.6.

## 8. Tapar, irse al mazo y jugadores inactivos

- **8.1 Tapar.** Poner una carta boca abajo **dentro de la zona de tirada** (fuera de la zona no cuenta). Si tapa una, tapa todas. Desde ese momento queda **inactivo**: sus cantos, respuestas y señas no valen. Las cartas tapadas siguen identificables y pueden mostrarse para acreditar el envido.
- **8.2 Caída accidental sobre la mesa.**
  - Boca abajo (dentro o fuera de la zona) → la recoge aclarando que fue accidental; no cuenta como jugada ni tapada.
  - Boca arriba **dentro** de la zona → cuenta como **jugada**.
  - Boca arriba **fuera** de la zona → la puede recoger.
- **8.3 Irse al mazo.** Diciendo "me voy al mazo" cuando la expresión es válida, o incorporando físicamente las cartas al mazo. Queda inactivo. Si solo lo dijo y sus cartas siguen identificables, puede mostrarlas **solo para acreditar el envido**. Una vez incorporadas al mazo, ya no.
- **8.4 Abandono colectivo.** "Nos vamos al mazo", dicho por un jugador **activo** en mano redonda, retira a **todo el equipo**. Dicho por un jugador inactivo, no vale.
- **8.5 Canto pendiente.** En mano redonda, si **un** jugador tapa o se va al mazo, eso no es respuesta del equipo: los compañeros activos todavía pueden responder. El abandono **colectivo** sí equivale a **rechazar** el canto. En pica-pica, tapar o irse al mazo **es rechazo** del canto pendiente.

## 9. Cartas jugadas, exhibidas, caídas y perdidas

- **9.1 Carta jugada.** Apoyada deliberadamente en la zona de tirada y soltada, o caída boca arriba dentro de la zona (8.2). No se puede retirar. Mientras la sostiene, el jugador puede mostrarla y cambiarla.
- **9.2 Caída al piso.** No cuenta como jugada aunque se haya visto; si se recupera, vuelve al jugador. Si ya estaba jugada y rebota al piso, sigue jugada.
- **9.3 Carta perdida e irrecuperable.** El jugador queda **inactivo** el resto de la mano (sus compañeros siguen; las rondas ya ganadas valen). Solo puede acreditar el envido con las cartas que conserve, y la carta perdida no se presume. Al terminar la mano se cambia el mazo. Si fue accidental, no hay sanción; si fue deliberado, sí. Si la carta aparece después, no se reincorpora.
- **9.4 Carta jugada que desaparece.** Se intenta reconstruir (acuerdo, posición, video). Si no se puede y fue accidental, el árbitro puede anular la mano. Si fue deliberado, nadie se beneficia y se aplica el cap. 19.
- **9.5 Carta jugada fuera de turno.** Queda jugada y visible. Se sigue el orden normal; cuando le toca al infractor, se considera que ya jugó esa carta.
- **9.6 Dos cartas jugadas.** Vale el orden en que quedaron. Si fueron simultáneas, el propio jugador declara cuál fue primero y eso queda firme.
- **9.7 Exhibición pública.** Un jugador activo puede mostrar sus cartas, siempre a **toda** la mesa.
- **9.8 Exhibición privada** (solo a un compañero): está prohibida. Hay que mostrar esa carta a todos; si se niega → advertencia disciplinaria (no cambia los puntos). Si fue para pasar información → cap. 19. Nadie puede dar vuelta ni exponer cartas de un rival.

## 10. Declaraciones verbales y respuestas

- **10.1 Primera expresión válida.** Si compañeros dicen cosas distintas, vale la **primera** expresión reglamentaria completa, clara y audible. Las expresiones compuestas se toman enteras ("no quiero" no contiene un "quiero").
- **10.2 Contexto.** En juego activo, toda expresión reglamentaria tiene efecto aunque se diga en broma, en una pregunta o por error (salvo jugadores de un duelo futuro de pica-pica o durante una suspensión formal del árbitro).
- **10.3 Perdón inmediato.** Una expresión accidental se puede anular de inmediato y de forma inequívoca si es una irregularidad menor: en mano redonda, de acuerdo ambos capitanes; en pica-pica, los dos del duelo. Si se sigue jugando a sabiendas, queda convalidada. Está prohibido guardarse un reclamo para usarlo según cómo salga la mano.
- **10.4 Respuestas válidas en mano redonda.**
  - Aceptar: `quiero`, `se quiere`, `queremos`.
  - Rechazar: `no quiero`, `no se quiere`, `no queremos`.
  - **No** son respuestas válidas: "al mazo", "dale", "sí", "vamos", "jugamos".
- **10.5 Respuestas válidas en pica-pica** (individuales): `quiero`, `se quiere`, `no quiero`, `no se quiere`. "Queremos" y "no queremos" **no** valen.

## 11. Envido

- **11.1 Cálculo.**
  - Las cartas del 1 al 7 valen su número; las figuras (10, 11, 12) valen 0.
  - Dos cartas del mismo palo: **20 + la suma** de sus valores.
  - Sin dos del mismo palo: vale la carta numérica más alta.
  - Con tres del mismo palo (no hay flor): se usan las dos que formen el tanto que corresponda (en la práctica, las dos más altas).
  - Rango posible: 0–7 sin pareja, 20–33 con pareja.
- **11.2 Momento.** Desde que termina el reparto hasta que el **último jugador de la primera ronda** juega su primera carta (con las reglas especiales de turnos y cantos pendientes).
- **11.3 Invitaciones.** Envido, real envido y falta envido, combinadas según el Anexo B.
- **11.4 Declaración.** Una vez querido, declara primero el **mano** y luego los demás en el orden de la mesa. En pica-pica declaran solo los dos del duelo (empieza el que es mano entre ellos). Vale el **primer número completo** dicho ("treinta y uno" es un solo número). No se puede corregir.
- **11.5 "Son buenas".** Reconoce que el jugador no supera el tanto rival. Incluye a los compañeros que debían declarar antes y se quedaron callados. No anula un número que ya dijo un compañero.
- **11.6 Empates.** Entre rivales con el mismo tanto, gana el que es **mano** respecto del otro. Si varios compañeros declararon el mismo tanto ganador, acredita el que es mano entre ellos.
- **11.7 Acreditación.** El ganador muestra las cartas necesarias para probar **exactamente** el número (no tiene que mostrar más).
  - Mano redonda: el rival puede reclamar hasta que se **corta el mazo** para la mano siguiente. Si el reclamo es a tiempo y el ganador no puede acreditar → **todos los puntos efectivamente disputados en esa mano** son para el rival.
  - Sin reclamo antes del corte → todo queda convalidado.
- **11.8 Declaración falsa de quien pierde el envido.** No tiene que mostrar sus cartas. Si quedan expuestas legítimamente a tiempo y prueban que no tenía lo que dijo → **todos los puntos de la mano** son para el rival.
- **11.9 Falta envido.**
  - Ambos equipos en **malas** → la falta envido querida **define el partido**.
  - Algún equipo en **buenas** → vale los puntos que le faltan al equipo que **va ganando** para llegar a 30.
  - En **pica-pica** → vale **6 puntos en total**, sin importar los cantos anteriores.
- **11.10 Partido terminado por envido.** Si la acreditación lleva a un equipo a 30, el partido termina en ese momento; el truco, retruco o vale cuatro pendiente queda sin efecto.
- **11.11 Truco cantado antes del envido.** Si se canta truco mientras el envido todavía se puede cantar, el rival puede **anteponer el envido**: se resuelve el envido y el truco queda pendiente (salvo un canto fuera de turno que venza, cap. 13).

## 12. Truco y cantos irregulares

- **12.1 Secuencia.** Truco → retruco → vale cuatro. Como regla general, solo **el equipo que aceptó** la instancia anterior puede subir.
- **12.2 Puntaje.**

| Situación | Puntos |
|---|---|
| Mano sin truco | 1 |
| Truco no querido | 1 |
| Truco querido | 2 |
| Retruco no querido | 2 |
| Retruco querido | 3 |
| Vale cuatro no querido | 3 |
| Vale cuatro querido | 4 |

- **12.3 Canto irregular.** Un retruco o vale cuatro fuera de secuencia o de un equipo sin derecho a subir. Queda **convalidado** si el rival lo responde válidamente o sigue jugando sin objetarlo a tiempo; desde ahí produce los mismos efectos que un canto regular.
- **12.4 Plazo para objetar.**
  - Si la respuesta permite seguir la mano → hasta que el jugador al que le toca juegue su carta.
  - Si un "no quiero" termina la mano → antes de que el equipo que cantó suelte sus cartas confiando en esa respuesta.
- **12.5 Perdón expreso.** En mano redonda, ambos capitanes pueden anular un canto accidental o irregular y volver al estado anterior (en pica-pica, los dos del duelo). Debe quedar claro el estado antes de seguir.

## 13. Cantos en turno y fuera de turno

- **13.1 En turno** está el jugador al que le toca jugar la próxima carta.
- **13.2 Canto en turno.** El rival debe resolverlo antes de seguir. **No vence** porque se juegue una carta.
- **13.3 Envido + truco en turno con carta jugada.** La carta queda jugada y ambos cantos siguen valiendo. Se resuelve primero el envido y después el truco.
- **13.4 Canto fuera de turno.** Un jugador activo que no está en turno puede cantar envido o truco. El rival puede responder ya o dejarlo pendiente.
- **13.5 Vencimiento.** Si el rival no responde y el jugador en turno **juega su carta**, todos los cantos fuera de turno sin responder **vencen** (quedan sin efecto).
- **13.6 Varios pendientes.** Con envido y truco pendientes fuera de turno, si el rival responde, se resuelve primero el envido. Después puede responder el truco o jugar su carta para dejarlo vencer.
- **13.7 "Sin ley de juego".** No existe en Se Pica TSA. La expresión no tiene efecto; los cantos válidos que se digan junto con ella se evalúan por separado.

## 14. Comunicación, idioma, conversación y señas

- **14.1 Idioma.** Español. Los cantos, respuestas y declaraciones solo valen en español con las expresiones reconocidas. Se permiten palabras extranjeras aisladas de uso común, siempre que no sean un canto o un código. Usar otro idioma para ocultar información = código no autorizado → advertencia disciplinaria.
- **14.2 Conversación.** En mano redonda los compañeros pueden hablar libremente. Se permiten la mentira, la chicana y la picardía, dentro de los límites de respeto e integridad.
- **14.3 Códigos prohibidos.** No se pueden usar palabras, números, gestos, objetos o patrones acordados de antemano para pasar información de cartas.
- **14.4 Señas oficiales.** Solo las del **Anexo C**, y se pueden usar de forma verdadera o falsa. Se prohíben señas inventadas o alteradas. No se puede tapar la cara para que no se vean las señas: primero advertencia verbal, después disciplinaria.

## 15. Pica-pica

- **15.1 Inicio y alternancia.**
  - Empieza en la mano **siguiente** a aquella en la que algún equipo **alcanza o supera 5 puntos**.
  - Desde ahí se **alterna**: mano redonda, mano de pica-pica, mano redonda...
  - Si durante una mano de pica-pica un equipo alcanza o supera **25**, se juegan igual los duelos que quedan de esa mano; desde la siguiente, todas son redondas.
  - Si llega a 25 en una mano redonda → todas las manos que siguen son redondas.
  - Si un equipo llega a **30** en cualquier momento → el partido termina de inmediato (no se juegan los duelos que faltan).
- **15.2 Cruces.** 1 vs 1, 2 vs 2, 3 vs 3 (numeración reservada).
- **15.3 Reparto.** Igual que en mano redonda (3 cartas a los 6 jugadores). **No** se vuelve a repartir entre duelos. Los 6 pueden mirar sus cartas.
- **15.4 Orden de los duelos.** El primero es el del jugador a la **derecha del mazo** contra el rival de su mismo número. Después se sigue el orden de la mesa hasta el primer jugador cuyo duelo no se jugó todavía (igual para el 3.º). En cada duelo es mano el que aparece primero hacia la derecha desde el mazo.
- **15.5 Duelos futuros.** Mientras se juega un duelo, los otros no empezaron. Las expresiones de jugadores de duelos futuros **no tienen efecto** (ni sanción si son accidentales). Decir "me voy al mazo" no tiene efecto, pero **incorporar físicamente** las cartas al mazo lo saca de su duelo. Tapar antes de su duelo no tiene efecto; las cartas siguen disponibles.
- **15.6 Interferencia.** Quienes no juegan el duelo en curso no pueden hacer señas, aconsejar, recordar cartas, declarar, responder ni intervenir. Exponer una carta accidentalmente no se sanciona; hacerlo a propósito para informar es interferencia.
  - Interfiere **un** equipo → el duelo sigue y **todos los puntos disputados en ese duelo** van al rival del infractor, más la sanción disciplinaria.
  - Interfieren **ambos** → el duelo se anula (0–0, no se repite) y ambos reciben sanción. Si las sanciones hicieran perder el partido a los dos, pierde por sanción el que interfirió **primero** (la sanción del otro queda registrada). Los demás duelos siguen si el partido continúa.
  - **Entre duelos** se permiten comentarios generales de aliento ("dale", "jugá", "tranquilo"). **No** se pueden comentar cartas vistas, dar instrucciones estratégicas específicas, hacer señas ni impulsar reclamos de un duelo ya terminado → advertencia disciplinaria (no se adjudican automáticamente los puntos del duelo siguiente).
- **15.7 Tapar o irse al mazo.** Rigen las reglas generales. Se pueden mostrar las cartas para acreditar el envido mientras sigan identificables. Si hay un canto pendiente, es **rechazo**.
- **15.8 Falta envido** = 6 puntos en total.
- **15.9 Acreditación y reclamo.** El rival del duelo puede reclamar hasta el **inicio efectivo del duelo siguiente** (cuando alguno de sus participantes juega una carta, canta envido o truco, tapa o se va al mazo). Si el ganador no puede acreditar → todos los puntos del duelo van al rival. En el **último duelo**, el plazo es hasta el corte de la mano siguiente.
- **15.10 Incidencias.** Las resuelven **solo los dos contendientes** (ni los capitanes ni los compañeros intervienen). Si uno pide al árbitro, se lo dice a su capitán y el duelo se **suspende en ese momento**; el capitán lo formaliza sin demora. Se aplica 17.3.

## 16. Marcador, sistema oficial y homologación

- **16.1** Cada equipo designa un responsable del marcador.
- **16.2 Verificación.** Al final de cada mano, ambos equipos verifican los puntos. En pica-pica se anotan los puntos **al terminar cada duelo**, pero la verificación conjunta se hace al terminar los 3 duelos (o antes, si alguien llega a 30). Las diferencias se plantean como máximo **antes del corte de la mano siguiente**; después, el resultado queda firme (salvo un error material reconocido por ambos o una cuestión de integridad).
- **16.3 Sistema oficial.** El resultado se registra en el sistema oficial Se Pica TSA; cada capitán accede desde un dispositivo autorizado.
- **16.4 Validación final.** Ambos capitanes validan → el resultado queda **homologado**.
- **16.5 Discrepancia.** Si un capitán no está de acuerdo o se niega a validar, interviene el árbitro, que puede revisar el marcador físico, los registros digitales y las cámaras, y homologa. Negarse sin justificación → sanción disciplinaria.
- **16.6 Falla tecnológica.** No suspende el partido: se sigue con marcador físico o registro manual y se carga después.
- **16.7 Credencial arbitral.** El árbitro puede homologar o corregir resultados sin la aceptación de un capitán.
- **16.8 Cierre.** La homologación cierra el resultado deportivo. Durante los **15 minutos** siguientes solo se pueden corregir errores **materiales o de carga** (puntaje mal ingresado, identificación equivocada, falla de registro); no se reabren manos, cantos ni reclamos. Las conductas ocurridas antes de homologar se pueden sancionar aunque un equipo ya haya llegado a 30. Lo que pase después de homologar no cambia el resultado, salvo fraude o integridad (revisión excepcional).

## 17. Árbitro, reclamos y revisión audiovisual

- **17.1** El árbitro es la máxima autoridad del partido; sus decisiones sobre una jugada son definitivas.
- **17.2** Solo el **capitán** pide formalmente la intervención. El jugador involucrado puede pedir una exhibición u objetar dentro del juego. En pica-pica, el pedido del contendiente a su capitán suspende el duelo.
- **17.3 Suspensión.** Con un reclamo formal, el juego se suspende y los **plazos se congelan**. Durante la suspensión nadie juega ni toca cartas, hace señas, canta, corta ni habla de estrategia. Las palabras reglamentarias dichas para explicar el reclamo no tienen efecto. Solo el árbitro reanuda el juego.
- **17.4** El reclamo puede plantearse en la mesa o en privado; la decisión se comunica a ambos equipos.
- **17.5 Plazos.** Solo sobre situaciones actuales o con plazo vigente. Las manos cerradas no se reabren (salvo un error de anotación reconocido por ambos o una cuestión de integridad).
- **17.6 Cámaras.** El árbitro puede revisar imágenes oficiales; si no alcanzan, resuelve con lo que tiene. No hay derecho automático a repetir la mano.
- **17.7 De oficio.** Por regla general, el árbitro interviene a pedido de un capitán. Interviene de oficio ante indicios de carteo, fraude, colusión, agresiones, amenazas, riesgos de seguridad o faltas graves de integridad.
- **17.8 Jefe de Árbitros.** Autoridad superior para casos no previstos, temas generales y conflictos que excedan un partido. **No** es una instancia automática de apelación.
- **17.9 Revisión excepcional** de partidos anteriores afectados por una falta grave o de integridad: la decide el Jefe de Árbitros. Una descalificación posterior no alcanza por sí sola para cambiar resultados anteriores.

## 18. Espectadores, asistencia externa e integridad

- **18.1** Los espectadores no pueden interferir; el árbitro puede pedir que se retiren. El equipo no se sanciona salvo que haya participado o coordinado.
- **18.2 Información accidental.** No se sanciona y, en general, la mano sigue. Solo se anula si hubo intervención intencional.
- **18.3 Asistencia externa deliberada** → advertencia disciplinaria; si hay coordinación o fraude, sanción mayor.
- **18.4 Integridad competitiva.** Está prohibido: arreglar resultados, perder a propósito, compartir información con el rival, acordar cantos o jugadas entre equipos, manipular resultados para favorecer o perjudicar a terceros, ofrecer o recibir dinero o beneficios, y apostar (1.12). Puede llevar a **descalificación inmediata**.

## 19. Advertencias, sanciones y descalificación

### Escala

```
Irregularidad leve  ──► Advertencia verbal (no es sanción, no cambia el marcador)
        │ reiteración
        ▼
Advertencia disciplinaria (se computa al EQUIPO)
        │ 2.ª en el mismo partido
        ▼
Pérdida del partido (Victoria por Sanción para el rival)

Falta grave / fraude / integridad ──► Sanción directa, incluso descalificación inmediata
```

- **19.1 Advertencia verbal** ante faltas leves sin consecuencia especial. Si se repite, puede convertirse en advertencia disciplinaria. Las irregularidades menores accidentales y corregibles **no** generan sanción automática. Los errores de reparto mantienen su propio contador (6.4).
- **19.2 Advertencias disciplinarias.**
  - Se computan al **equipo**.
  - **2.ª advertencia en el mismo partido → pierde el partido.**
  - La acumulación entre partidos, la descalificación por acumulación y el reinicio del contador entre la etapa clasificatoria y la televisada los definen las **Condiciones Particulares**.
  - Si la misma advertencia es la 2.ª del partido y además causal de descalificación acumulada → se aplican **ambas** consecuencias, y el rival registra **Victoria por Descalificación**.
  - El régimen disciplinario sigue vigente hasta la homologación.
- **19.3 Conductas que pueden generar advertencia disciplinaria:**
  - Interferencia en un duelo de pica-pica.
  - Señas, palabras clave, otro idioma o códigos no autorizados.
  - Buscar o aprovechar información externa.
  - Uso indebido de celulares, smartwatches, auriculares u otros dispositivos.
  - Demorar el juego a propósito o en forma reiterada, o presentarse tarde.
  - Negarse a cumplir una decisión del árbitro.
  - Falta de respeto grave, hostigamiento, intimidación o conducta antideportiva (que no llegue a descalificación).
  - Alterar el marcador o el registro del resultado.
  - Cambiar a propósito las posiciones asignadas.
  - Dejar la mesa sin autorización.
  - Negarse sin justificación a validar el resultado en el sistema oficial.
  - Usar los reclamos en forma abusiva para demorar (un reclamo de buena fe no se sanciona).
  - Jugar, tocar cartas, hacer señas o hablar de estrategia durante una suspensión.
  - Apostar o entrar a plataformas de apuestas.
  - Según las circunstancias, también: repetir manipulaciones ya advertidas, taparse la cara, negarse a mostrar a todos una carta exhibida en privado, o comunicarse entre duelos de pica-pica.
- **19.4 Carteo, fraude e integridad.** Carteo = toda manipulación deliberada del mazo, corte, mezcla, reparto o cartas para obtener ventaja (acomodar, reservar, sacar de una posición no autorizada, esconder, sustituir o intercambiar cartas). → **Descalificación inmediata** posible, sin advertencias previas; el árbitro interviene de oficio. También pueden llevar a descalificación: asistencia externa organizada, códigos acordados, colusión, arreglo de partidos, perder a propósito para beneficiar a un tercero, manipular resultados y sobornos.
- **19.5 Conductas extremas → descalificación inmediata:** agresión física o intento, amenazas graves, daño deliberado, fraude o carteo, colusión o arreglo, poner en riesgo la seguridad, y volver a alterar las posiciones después de una corrección del árbitro.
- **19.6 Alteración deliberada de cartas o pruebas.** Nadie se beneficia de una irregularidad que provocó a propósito. Según la gravedad, el árbitro puede: (a) restablecer y aplicar una advertencia disciplinaria; (b) dar al rival **todos los puntos disputados** de la mano o duelo; (c) declarar la **pérdida del partido** (Victoria por Sanción); (d) **descalificar**. Si ambos equipos cometen conductas extremas → **Doble Descalificación**.
- **19.7 Régimen propio.** Tienen su propia consecuencia: errores del repartidor (6.4), ocultamiento de cantidad incorrecta (6.6), interferencias en pica-pica (15.6) e integridad. Lo leve sin régimen propio se rige por 19.1.
- **19.8 No convalidables.** Los equipos no pueden perdonar faltas graves de integridad, fraude, carteo, colusión, asistencia externa organizada, agresiones ni amenazas. El árbitro puede intervenir aunque nadie reclame.

## 20. Partidos televisados

- **20.1** Mismas reglas que cualquier otro partido.
- **20.2** Los jugadores no pueden recibir información de monitores, comentaristas, producción ni nada de la transmisión.
- **20.3** Las decisiones deportivas son solo del árbitro o del Jefe de Árbitros; la producción no tiene facultades arbitrales.
- **20.4 Protocolo Operativo de Televisión.** Regula solo aspectos técnicos y de producción y no cambia las reglas ni las sanciones. La producción no puede interrumpir una mano sin autorización del árbitro (salvo emergencia).
- **20.5 Marcas e indumentaria.** No se pueden mostrar marcas de terceros sin autorización escrita (cláusula XVI de los TyC). La indumentaria provista por el Organizador es obligatoria; no usarla puede llevar a quedar fuera de la transmisión y a una advertencia disciplinaria.

---

## Anexo A. Jerarquía de las cartas para el truco

| Orden | Carta o grupo |
|---|---|
| 1 | 1 de espadas |
| 2 | 1 de bastos |
| 3 | 7 de espadas |
| 4 | 7 de oros |
| 5 | Todos los 3 |
| 6 | Todos los 2 |
| 7 | 1 de oros y 1 de copas |
| 8 | Todos los 12 |
| 9 | Todos los 11 |
| 10 | Todos los 10 |
| 11 | 7 de copas y 7 de bastos |
| 12 | Todos los 6 |
| 13 | Todos los 5 |
| 14 | Todos los 4 |

(Menor orden = mayor valor. Las cartas del mismo grupo **empatan** → parda si son de equipos rivales.)

```ts
// Sugerencia: mayor número = carta más fuerte
const HIERARCHY: Record<string, number> = {
  "1-espada": 14, "1-basto": 13, "7-espada": 12, "7-oro": 11,
  "3-*": 10, "2-*": 9, "1-oro": 8, "1-copa": 8,
  "12-*": 7, "11-*": 6, "10-*": 5, "7-copa": 4, "7-basto": 4,
  "6-*": 3, "5-*": 2, "4-*": 1,
};
```

## Anexo B. Envido: valores, secuencias y puntajes

### B.1 Valores básicos

Las cartas del 1 al 7 valen su número; las figuras (10, 11, 12) valen 0. Dos cartas del mismo palo suman 20 más sus valores. Sin pareja del mismo palo, vale la carta numérica más alta.

```ts
function envido(cartas: {numero: number, palo: string}[]): number {
  const v = (n: number) => (n >= 10 ? 0 : n);
  let mejor = Math.max(...cartas.map(c => v(c.numero)));
  for (let i = 0; i < cartas.length; i++)
    for (let j = i + 1; j < cartas.length; j++)
      if (cartas[i].palo === cartas[j].palo)
        mejor = Math.max(mejor, 20 + v(cartas[i].numero) + v(cartas[j].numero));
  return mejor;
}
```

### B.2 Secuencias y puntajes

| Canto | Querido | No querido |
|---|---|---|
| Envido | 2 | 1 |
| Real envido | 3 | 1 |
| Falta envido | Según marcador* | 1 |
| Envido – envido | 4 | 2 |
| Envido – real envido | 5 | 2 |
| Envido – falta envido | Según marcador* | 2 |
| Real envido – falta envido | Según marcador* | 3 |
| Envido – envido – falta envido | Según marcador* | 4 |
| Envido – envido – real envido | 7 | 4 |
| Envido – real envido – falta envido | Según marcador* | 5 |
| Envido – envido – real envido – falta envido | Según marcador* | 7 |

\* Ver B.3.

Regla práctica que cumple la tabla: **no querido = suma de lo ya querido antes del último canto** (con mínimo 1). Querido sin falta = suma de los valores de cada canto (envido = 2, real envido = 3).

### B.3 Falta envido

- **Mano redonda:** se rige por 11.9. Si ambos equipos están en malas, define el partido; si alguno está en buenas, vale los puntos que le faltan al equipo que va adelante para llegar a 30.
- **Pica-pica:** vale **6 puntos en total**, sin importar las invitaciones anteriores.

```ts
type Canto = "envido" | "real_envido" | "falta_envido";
const VALOR = { envido: 2, real_envido: 3 };

function puntosEnvido(
  cantos: Canto[], querido: boolean,
  ctx: { picaPica: boolean; ptsA: number; ptsB: number }
): number | "partido" {
  const previos = cantos.slice(0, -1);
  if (!querido)
    return Math.max(1, previos.reduce((s, c) => s + (VALOR as any)[c], 0));
  if (cantos.at(-1) === "falta_envido") {
    if (ctx.picaPica) return 6;
    const lider = Math.max(ctx.ptsA, ctx.ptsB);
    if (ctx.ptsA <= 15 && ctx.ptsB <= 15) return "partido"; // ambos en malas
    return 30 - lider;
  }
  return cantos.reduce((s, c) => s + (VALOR as any)[c], 0);
}
```

## Anexo C. Señas oficiales Se Pica TSA

### C.1 Regla de uso

- Solo valen las señas de este anexo. Una seña puede ser **verdadera o falsa**: hacerla no obliga a tener esa carta o combinación.
- Está prohibido usar otros gestos, palabras, objetos o patrones acordados, o modificar una seña oficial para crear un código adicional.
- No se puede tapar la cara ni impedir que los rivales vean las señas.
- "Derecha" e "izquierda" se interpretan desde la perspectiva del jugador que hace la seña.
- Si en el futuro hay ilustraciones, son didácticas: ante cualquier diferencia, prevalece el texto.

### C.2 Lista oficial

| N.º | Carta / situación | Gesto |
|---|---|---|
| 01 | As de espadas (ancho de espadas) | Levantar ambas cejas |
| 02 | As de bastos (ancho de bastos) | Guiñar el ojo derecho |
| 03 | Siete de espadas (siete bravo) | Desplazar la comisura de los labios hacia la derecha |
| 04 | Siete de oros | Desplazar la comisura de los labios hacia la izquierda |
| 05 | Cualquier tres | Morder suavemente el labio inferior |
| 06 | Cualquier dos | Fruncir y proyectar los labios hacia adelante (beso) |
| 07 | Anchos falsos (as de copas o as de oros) | Abrir ligeramente la boca |
| 12 | Buen envido | Fruncir la nariz |

### C.3 Alcance

- Las cartas o situaciones que no están en la lista (por ejemplo 7 de copas o de bastos, 4, 5, 6 y las figuras: sota, caballo y rey) **no tienen seña autorizada**. Tampoco hay seña para indicar que no se tienen cartas buenas para el truco. Los números 08, 09, 10 y 11 de la lista quedan sin uso.
- No hay seña de flor, porque se juega sin flor.
- En pica-pica, solo los dos jugadores del duelo en curso pueden hacer señas. Un jugador que no participa del duelo no puede usar una seña para pasarle información a su compañero.

---

## Notas para el desarrollo

1. **Máquina de estados de la mano:** `reparto → (posible incidencia de reparto) → rondas 1..3 con cantos intercalados → resolución de envido/truco → anotación → verificación → corte de la siguiente (cierra los plazos de reclamo)`.
2. **El corte de la mano siguiente es un evento clave:** cierra los reclamos de acreditación del envido (11.7), las diferencias de anotación (16.2) y el último duelo de pica-pica (15.9).
3. **Selector de tipo de mano:** `siguiente = (algún equipo ≥ 25) ? redonda : (pica-pica activado por haber llegado a ≥ 5 ? alternar : redonda)`. El pica-pica empieza en la mano **siguiente** a llegar a 5 puntos, y la alternancia arranca con pica-pica.
4. **Chequear 30 después de cada adjudicación de puntos**, incluso a mitad de un pica-pica o al acreditar un envido (11.10, 15.1), y recortar al tope de 30 (1.5).
5. **"Puntos efectivamente disputados"** (11.7, 11.8, 15.6, 15.9, 19.6) se refiere a todo lo que se jugó en esa mano o duelo (envido + truco); conviene guardar ese total por mano y por duelo para poder reasignarlo completo.
6. **Errores de reparto:** contador `{partidoId, jugadorId} → 0|1`; al llegar a 2 → +2 al rival, se anula la mano, el contador vuelve a 0 y el mazo pasa al siguiente repartidor.
7. **Advertencias disciplinarias:** contador por equipo y partido; al llegar a 2 → `VictoriaPorSancion` para el rival (o `VictoriaPorDescalificacion` si coincide con una descalificación).
8. **Configuración por edición** (no está fija en este reglamento): composición de grupos y cuadro, cupos por fase, mejores segundos, acumulación de advertencias entre partidos y su reinicio entre la etapa clasificatoria y la televisada.
9. **Error del original:** en 1.8 falta un verbo ("Las Condiciones Particulares de cada edición [establecerán] la composición…"). Está así también en la web.
10. **Malas/buenas en el código:** un equipo está en malas con 0–15 puntos y en buenas con 16–30. La falta envido "define el partido" solo si **ambos** tienen ≤ 15.
11. **Señas:** si el sistema lleva registro de incidencias, conviene guardar el catálogo C.2 como enum (`SENA_01`…`SENA_07`, `SENA_12`) para poder tipificar reclamos por señas no autorizadas (14.4, 19.3).
