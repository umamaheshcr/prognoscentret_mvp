/* Interface chrome, English and Swedish.
 *
 * Server-supplied strings (driver labels, warnings, guard messages, chapter
 * text) are translated in app/i18n.py and arrive already localised.
 *
 * Not translated, on purpose: publication titles and DST table codes. A source
 * is cited in its own language or the reader cannot find it.
 */
const T = {
  en: {
    lang_name: "English",
    gate0: "Gate 0 · fresh?", gate1: "Forecast",
    gate2: "Gate 2 · sign-off", gate3: "Gate 3 · red pen", pub: "Publish",
    gate1b: "Gate 1b · overlay",
    v_production: "Production",
    v_reason_label: "Reason (required only if you change the number)",
    tip_state_unchanged: "Not yet decided for any year.",
    tip_state_approved: "Every year decided, all at the agent's estimate.",
    tip_state_moved: "Decided, and at least one year moved away from the agent.",
    tip_state_partial: "Some years decided, some still open.",
    tip_state_no_estimate: "No institution publishes this number, so there is nothing to accept.",
    tip_actual: "Realised building starts, from the endogenous master file.",
    tip_fitted: "What the model produces over the years it was fitted on. The gap to the actual line is the error you can see.",
    tip_agent_line: "The forecast from the agent's own driver values, before you moved anything.",
    tip_model_line: "The model's forecast before your gate-1b overlay was applied.",
    tip_your_line: "The forecast after your driver decisions and any overlay.",
    tip_band: "One standard error either side, in logs — so it is wider above than below.",
    tip_holdout: "The last eight quarters were held back, the model refitted without them, and scored on them. Lower is better.",
    tip_demo: "Linear regression on two drivers, not the production ensemble. Chosen so slider response is smooth and attribution exact.",
    tip_kpi: "Annual total of the quarterly forecast. The bottom line compares it with the agent's own proposal.",
    tip_agent_bar: "The agent's annual total.",
    tip_your_bar: "Your annual total, after every decision you have made.",
    tip_band_p: "p10 to p90 of the institutions' numbers — where the middle 80 per cent sit.",
    tip_band_inst: "One institution's number. Hover a tick to see which.",
    tip_band_agent: "The agent's triangulated estimate.",
    tip_band_mine: "Your value.",
    tip_quality: "How well the year is covered: A means several sources print the number, B means it is thin.",
    tip_weight: "Share of the triangulation. Tier, recency, definition match, independence and past accuracy all feed it.",
    tip_tier: "1 is an official or statistical source, 2 a commercial forecaster, 3 trade press or sentiment.",
    tip_consensus: "Whether this source is allowed to form the consensus. Some are kept for calibration only.",
    tip_claims: "How many driver-years this source contributes a number to.",
    tip_latest: "The most recent publication we hold from this source, and its age.",
    tip_stale: "Older than six months. Gate 0 is where you decide whether that is still good enough to open the round.",
    tip_quote: "The sentence as printed in the source. If it cannot be found again, the number is discarded.",
    g0_silent: "declared and silent this vintage",
    verify: "Gate 1 · drivers", run: "Run",
    v_h: "Market-driver assumptions · gate 1",
    v_lede: "One assumption per forecast year, with the sources behind it. " +
      "No forecast on this page — approving a driver should not be steered by " +
      "watching a forecast line move while you do it.",
    v_approve_all: "Approve all unchanged",
    v_of: "of", v_approved: "approved", v_moved: "moved",
    v_drivers: "drivers", v_cells: "driver-years",
    v_carried: "carried by hand",
    v_no_estimate: "no estimate · coverage none",
    v_pick: "Pick a driver on the left.",
    v_latest_actual: "Latest actual",
    v_your_estimate: "Your estimate, year by year",
    v_agent_est: "the agent's estimate",
    v_sources: "Sources", v_institution: "Institution", v_value: "Value",
    v_weight: "Weight", v_published: "Published", v_report: "Report",
    v_quote: "Quote", v_excluded: "excluded from the consensus",
    v_accept: "Accept", v_move: "Move it", v_clear: "Clear",
    v_reason_ph: "Why does the agent's estimate not hold? In your own words.",
    v_no_reason_needed: "Accepting the agent's estimate needs no reason.",
    v_quality: "quality", v_consensus: "consensus", v_thin: "thin",
    v_used_by: "used by segments", v_cited_in: "cited in chapters",
    v_in_model: "reaches the model", v_report_only: "report text only",
    v_derived: "derived from", v_no_est_help:
      "No institution publishes this number for this year. Set a value by hand " +
      "if you are willing to carry it, or leave the cell empty.",

    run_h: "Run monitor · orchestrator",
    run_lede: "The round as workflow state: what each step read, how long it " +
      "took, what it logged, and where it is waiting. Separate from the " +
      "analyst's pages on purpose.",
    run_new: "New run", run_step: "Run", run_pass: "Pass gate",
    run_reset: "Reset from here", run_log: "Event log",
    run_status: "Status", run_step_col: "Step", run_ms: "ms",
    run_attempts: "Attempts", run_cost: "Cost", run_reads: "Reads",
    run_done: "done", run_waiting: "waiting for the analyst",
    g1b_h: "Analyst overlay · gate 1b",
    g1b_lede: "Set the forecast level by hand, where no driver carries the judgement. " +
      "You set the year; the model keeps the within-year shape.",
    g1b_warn: "This is the one number with no model behind it. It is kept as a " +
      "separate layer, never blended: the model line stays on the chart, the " +
      "decomposition shows the overlay as judgement rather than cause, and the " +
      "published chapter names you as its source. The backtest cannot validate " +
      "an overlay — it scores the model.",
    ov_chart_h: "Model against overlay",
    ov_chart_sub: "Grey dashed is the model under your approved drivers. Magenta is " +
      "the forecast after your overlay. Where they coincide, no overlay is set.",
    ov_model: "model", ov_yours_h: "yours", ov_set: "set by hand", ov_clear: "clear",
    ov_title: "Set the level", ov_modal_sub:
      "The model's value is stored beside yours, and your reason is carried into " +
      "the published chapter as the source for this number.",
    ov_ph2: "Why does the model not carry this? In your own words.",
    ov_keep2: "An overlay is measurable against the outcome but not against the " +
      "method. A round where overlays carry most of the movement is a round where " +
      "the model has stopped producing the forecast.",
    ov_commit2: "Commit overlay", ov_none: "no overlay set for this segment",
    ov_judgement: "analyst judgement · not attributable to a driver",
    sources_as_of: "sources as of",

    g0_h: "Source register", g0_lede:
      "The round starts because you say so, not because a date arrived. " +
      "Reject a source as too old or too thin and the reason is journalled.",
    g0_open: "Open the round", g0_opened: "Round open",
    g0_reject: "reject", g0_rejected: "rejected",
    g0_fetch: "fetchable", g0_upload: "upload task",
    g0_empty: "Gate 0 has no recorded history in the production chain — " +
      "nothing was ever journalled here. It starts empty on purpose.",
    g0_reason: "Why is this source not good enough to open the round?",

    g1_h: "Market drivers · gate 1", g1_lede:
      "You approve every value. Drag a slider and the forecast redraws live — " +
      "nothing is committed until you give a reason.",
    g1_inert_h: "Present, but not wired",
    g1_inert_lede: "The apartment price path the model cannot use.",
    reset: "Reset to agent", commit: "Commit with reason", undo: "Undo",
    source: "source", agent: "agent",
    not_in_model: "not in model", not_wired: "not wired",

    g2_h: "Config rows · gate 2", g2_lede:
      "You adjust the config row, never the number. A hand-edited value is " +
      "untraceable; a weight is not. The backtest is the referee.",
    g2_driver: "Tobin's Q series", g2_transform: "transform",
    g2_rate: "include the rate", g2_seasonals: "seasonal dummies",
    g2_apply: "Apply config row", g2_signoff: "Sign off",
    g2_signoff_reason: "What did the backtest teach? A missing driver is research, not code.",
    g2_before: "before", g2_after: "after",

    g3_h: "The chapter · gate 3", g3_lede:
      "Every figure carries its binding. Edit a sentence and the correction is " +
      "journalled; if it returns it becomes a numbered style rule.",
    g3_edit: "Edit the text", g3_reason: "Why does the house write it this way?",
    g3_save: "Journal the correction", g3_recheck: "Re-run the check",
    g3_style: "House rules honoured here",

    pub_h: "Published", pub_lede:
      "The check binds every number to a source, or the publish does not happen. " +
      "In production this exits 1.",
    pub_do: "Publish", pub_sources: "Sources — built by machine, not typed",
    pub_bound: "numbers bound to a source", pub_refused: "Publish refused",

    chart_starts: "new starts", moved_h: "What moved it", moved_lede:
      "Exact attribution. In logs the model is additive, so each driver's " +
      "effect is its coefficient times its change — no residual.",
    net: "Net effect on starts",
    annual_total: "Annual total", agent_fc: "Agent's forecast",
    your_fc: "Your forecast", diff: "Difference",
    as_agent: "as the agent proposed", vs_agent: "vs agent",
    forecast: "forecast", actual: "actual", fitted: "fitted",
    agent_line: "agent forecast", your_line: "your forecast", band: "±1 se band",
    annual_note: "annual totals · grey = agent, magenta = yours",
    live: "live · server", roundtrip: "round trip", driver: "driver",

    diag_h: "Model diagnostics", diag_lede:
      "Fitted at start-up on the frozen snapshot. Signs are a test, not a " +
      "formality: Tobin's Q must be positive and the rate negative.",
    segment: "Segment", sample: "Sample", holdout: "Hold-out MAPE", signs: "Signs",
    signs_ok: "✓ as config", signs_bad: "✗ WRONG",

    journal_h: "Journal", journal_lede:
      "Append-only, one journal for every gate. Your own words, kept verbatim.",
    journal_empty: "nothing recorded this session",
    repeated: "A correction has returned",
    repeated_note: "Twice is a systematic fault in the agent, not a special case.",

    honest_h: "Honest status",
    honest_1: "<b>This is a demo model.</b> Linear regression on two drivers, chosen " +
      "so slider response is smooth and attribution exact — not the production " +
      "ensemble, whose weights were set by hold-out backtest. It is less accurate, " +
      "and the figure beside each segment says by how much.",
    honest_2: "<b>No language model runs anywhere in this pilot.</b> Zero tokens, no " +
      "API key, no network call. P1's research is a frozen snapshot and the chapter " +
      "is assembled by a deterministic template, not by P3's writer.",
    honest_3: "<b>What it does not prove:</b> that the research agent works unattended, " +
      "that the learning loop closes, that the chain carries a second country, or " +
      "that any of it runs when the laptop is off.",

    ov_h: "Override", ov_sub:
      "The reason is kept verbatim and the agent reads it before the next round. " +
      "A paraphrase is already an interpretation.",
    ov_agent: "agent proposed", ov_yours: "your value",
    ov_ph: "Why? In your own words.",
    ov_keep: "The agent's value is kept beside yours, so a later round can measure " +
      "which was closer.",
    ov_commit: "Commit override", cancel: "Cancel", close: "Close",
    committed: "Journalled verbatim. The agent reads this before the next round.",
    need_reason: "A reason is required — that is the design, not a form validation.",
    no_quote: "No verbatim quote has been lifted from the source document into this " +
      "pilot. The production chain requires one before a number may be used — a " +
      "number must be PRINTED, and the quote must be re-findable word for word. " +
      "Showing an invented quote here would defeat the control this panel exists " +
      "to demonstrate.",
    efter_note: "found in the file itself, not typed here",
    institutions: "Institutions", guard: "guard",
    no_bounds: "no hard bounds declared",
    declared_in_config: "declared in config",
    not_used: "Not used by the model.",
  },

  sv: {
    lang_name: "Svenska",
    gate0: "Grind 0 · färsk?", gate1: "Prognos",
    gate2: "Grind 2 · godkännande", gate3: "Grind 3 · rödpenna", pub: "Publicera",
    gate1b: "Grind 1b · påslag",
    v_production: "Produktion",
    v_reason_label: "Skäl (krävs bara om du ändrar talet)",
    tip_state_unchanged: "Ännu inte avgjord för något år.",
    tip_state_approved: "Alla år avgjorda, samtliga på agentens skattning.",
    tip_state_moved: "Avgjord, och minst ett år flyttat från agentens värde.",
    tip_state_partial: "Vissa år avgjorda, andra öppna.",
    tip_state_no_estimate: "Ingen institution publicerar talet, så det finns inget att godta.",
    tip_actual: "Realiserade byggstarter, ur den endogena masterfilen.",
    tip_fitted: "Vad modellen ger över de år den anpassades på. Avståndet till utfallslinjen är felet du kan se.",
    tip_agent_line: "Prognosen med agentens egna drivarvärden, innan du ändrade något.",
    tip_model_line: "Modellens prognos innan ditt påslag i grind 1b lades på.",
    tip_your_line: "Prognosen efter dina drivarbeslut och eventuellt påslag.",
    tip_band: "En standardavvikelse på var sida, i logaritmer — därför bredare uppåt än nedåt.",
    tip_holdout: "De sista åtta kvartalen hölls undan, modellen anpassades om utan dem och bedömdes på dem. Lägre är bättre.",
    tip_demo: "Linjär regression på två drivare, inte produktionsensemblen. Vald för att reglagets svar ska bli jämnt och uppdelningen exakt.",
    tip_kpi: "Årssumma av kvartalsprognosen. Nedersta raden jämför med agentens eget förslag.",
    tip_agent_bar: "Agentens årssumma.",
    tip_your_bar: "Din årssumma, efter alla beslut du fattat.",
    tip_band_p: "p10 till p90 av institutionernas tal — där de mittersta 80 procenten ligger.",
    tip_band_inst: "En institutions tal. Håll över ett streck för att se vilken.",
    tip_band_agent: "Agentens triangulerade skattning.",
    tip_band_mine: "Ditt värde.",
    tip_quality: "Hur väl året är täckt: A betyder att flera källor trycker talet, B att det är tunt.",
    tip_weight: "Andel av trianguleringen. Nivå, aktualitet, definitionsmatchning, oberoende och tidigare träffsäkerhet påverkar den.",
    tip_tier: "1 är en officiell eller statistisk källa, 2 en kommersiell prognosmakare, 3 fackpress eller sentiment.",
    tip_consensus: "Om källan får bilda konsensus. Vissa behålls bara för kalibrering.",
    tip_claims: "Hur många drivarår källan bidrar med ett tal till.",
    tip_latest: "Den senaste publikationen vi har från källan, och dess ålder.",
    tip_stale: "Äldre än sex månader. I grind 0 avgör du om det ändå räcker för att öppna rundan.",
    tip_quote: "Meningen som den är tryckt i källan. Kan den inte återfinnas förkastas talet.",
    g0_silent: "deklarerade och tysta denna årgång",
    verify: "Grind 1 · drivare", run: "Körning",
    v_h: "Antaganden om marknadsdrivare · grind 1",
    v_lede: "Ett antagande per prognosår, med källorna bakom. Ingen prognos på " +
      "den här sidan — att godkänna en drivare ska inte styras av att man ser " +
      "en prognoslinje röra sig samtidigt.",
    v_approve_all: "Godkänn alla oförändrade",
    v_of: "av", v_approved: "godkända", v_moved: "flyttade",
    v_drivers: "drivare", v_cells: "drivarår",
    v_carried: "burna för hand",
    v_no_estimate: "inget skattat värde · ingen täckning",
    v_pick: "Välj en drivare till vänster.",
    v_latest_actual: "Senaste utfall",
    v_your_estimate: "Ditt antagande, år för år",
    v_agent_est: "agentens skattning",
    v_sources: "Källor", v_institution: "Institution", v_value: "Värde",
    v_weight: "Vikt", v_published: "Publicerad", v_report: "Rapport",
    v_quote: "Citat", v_excluded: "utesluten ur konsensus",
    v_accept: "Godkänn", v_move: "Ändra", v_clear: "Rensa",
    v_reason_ph: "Varför håller inte agentens skattning? Med dina egna ord.",
    v_no_reason_needed: "Att godta agentens skattning kräver inget skäl.",
    v_quality: "kvalitet", v_consensus: "konsensus", v_thin: "tunn",
    v_used_by: "används av segment", v_cited_in: "citerad i kapitel",
    v_in_model: "går in i modellen", v_report_only: "endast rapporttext",
    v_derived: "härledd ur", v_no_est_help:
      "Ingen institution publicerar detta tal för året. Sätt ett värde för hand " +
      "om du är beredd att bära det, eller lämna cellen tom.",

    run_h: "Körningsövervakning · orkestrerare",
    run_lede: "Rundan som arbetsflödestillstånd: vad varje steg läste, hur lång " +
      "tid det tog, vad det loggade och var det väntar. Avsiktligt skilt från " +
      "analytikerns sidor.",
    run_new: "Ny körning", run_step: "Kör", run_pass: "Passera grind",
    run_reset: "Återställ härifrån", run_log: "Händelselogg",
    run_status: "Status", run_step_col: "Steg", run_ms: "ms",
    run_attempts: "Försök", run_cost: "Kostnad", run_reads: "Läser",
    run_done: "klar", run_waiting: "väntar på analytikern",
    g1b_h: "Analytikerns påslag · grind 1b",
    g1b_lede: "Sätt prognosnivån för hand, där ingen drivare bär bedömningen. " +
      "Du sätter året; modellen behåller formen inom året.",
    g1b_warn: "Detta är det enda talet utan en modell bakom sig. Det hålls som ett " +
      "eget lager, aldrig inblandat: modellinjen ligger kvar i diagrammet, " +
      "uppdelningen visar påslaget som bedömning och inte som orsak, och det " +
      "publicerade kapitlet anger dig som källa. Backtestet kan inte validera ett " +
      "påslag — det bedömer modellen.",
    ov_chart_h: "Modell mot påslag",
    ov_chart_sub: "Grå streckad är modellen med dina godkända drivare. Magenta är " +
      "prognosen efter ditt påslag. Där de sammanfaller finns inget påslag.",
    ov_model: "modell", ov_yours_h: "ditt", ov_set: "satt för hand", ov_clear: "rensa",
    ov_title: "Sätt nivån", ov_modal_sub:
      "Modellens värde sparas vid sidan av ditt, och ditt skäl följer med in i det " +
      "publicerade kapitlet som källa för detta tal.",
    ov_ph2: "Varför bär modellen inte detta? Med dina egna ord.",
    ov_keep2: "Ett påslag kan mätas mot utfallet men inte mot metoden. En runda där " +
      "påslagen bär största delen av rörelsen är en runda där modellen har slutat " +
      "producera prognosen.",
    ov_commit2: "Bokför påslag", ov_none: "inget påslag satt för detta segment",
    ov_judgement: "analytikerns bedömning · kan inte hänföras till en drivare",
    sources_as_of: "källor per",

    g0_h: "Källregister", g0_lede:
      "Rundan startar för att du säger det, inte för att ett datum kom. " +
      "Avvisa en källa som för gammal eller för tunn och skälet journalförs.",
    g0_open: "Öppna rundan", g0_opened: "Rundan är öppen",
    g0_reject: "avvisa", g0_rejected: "avvisad",
    g0_fetch: "hämtningsbar", g0_upload: "uppladdning krävs",
    g0_empty: "Grind 0 har ingen historik i produktionskedjan — inget har någonsin " +
      "journalförts här. Den startar tom med avsikt.",
    g0_reason: "Varför är källan inte tillräcklig för att öppna rundan?",

    g1_h: "Marknadsdrivare · grind 1", g1_lede:
      "Du godkänner varje värde. Dra i ett reglage och prognosen ritas om direkt — " +
      "inget bokförs innan du anger ett skäl.",
    g1_inert_h: "Finns, men inte inkopplad",
    g1_inert_lede: "Prisbanan för lägenheter som modellen inte kan använda.",
    reset: "Återställ till agenten", commit: "Bokför med skäl", undo: "Ångra",
    source: "källa", agent: "agent",
    not_in_model: "ej i modellen", not_wired: "ej inkopplad",

    g2_h: "Konfigurationsrader · grind 2", g2_lede:
      "Du ändrar konfigurationsraden, aldrig talet. Ett handredigerat värde är " +
      "ospårbart; en vikt är det inte. Backtestet är domaren.",
    g2_driver: "Tobins Q-serie", g2_transform: "transform",
    g2_rate: "inkludera räntan", g2_seasonals: "säsongsdummies",
    g2_apply: "Tillämpa raden", g2_signoff: "Godkänn",
    g2_signoff_reason: "Vad lärde backtestet? En saknad drivare är research, inte kod.",
    g2_before: "före", g2_after: "efter",

    g3_h: "Kapitlet · grind 3", g3_lede:
      "Varje tal bär sin bindning. Redigera en mening och rättelsen journalförs; " +
      "återkommer den blir den en numrerad stilregel.",
    g3_edit: "Redigera texten", g3_reason: "Varför skriver huset så?",
    g3_save: "Journalför rättelsen", g3_recheck: "Kör kontrollen igen",
    g3_style: "Husregler som följs här",

    pub_h: "Publicerad", pub_lede:
      "Kontrollen binder varje tal till en källa, annars sker ingen publicering. " +
      "I produktion avslutas körningen med 1.",
    pub_do: "Publicera", pub_sources: "Källor — maskinbyggda, inte inskrivna",
    pub_bound: "tal bundna till en källa", pub_refused: "Publicering avvisad",

    chart_starts: "nya igångsättningar", moved_h: "Vad flyttade den", moved_lede:
      "Exakt uppdelning. I logaritmer är modellen additiv, så varje drivares " +
      "effekt är dess koefficient gånger dess förändring — ingen restpost.",
    net: "Nettoeffekt på igångsättningar",
    annual_total: "Årssumma", agent_fc: "Agentens prognos",
    your_fc: "Din prognos", diff: "Skillnad",
    as_agent: "som agenten föreslog", vs_agent: "mot agenten",
    forecast: "prognos", actual: "utfall", fitted: "anpassad",
    agent_line: "agentens prognos", your_line: "din prognos", band: "±1 se-band",
    annual_note: "årssummor · grått = agenten, magenta = du",
    live: "direkt · server", roundtrip: "tur och retur", driver: "drivare",

    diag_h: "Modelldiagnostik", diag_lede:
      "Anpassad vid start på det frysta urvalet. Tecknen är ett test, inte en " +
      "formalitet: Tobins Q ska vara positiv och räntan negativ.",
    segment: "Segment", sample: "Urval", holdout: "Hold-out MAPE", signs: "Tecken",
    signs_ok: "✓ som konfigurationen", signs_bad: "✗ FEL",

    journal_h: "Journal", journal_lede:
      "Endast tillägg, en journal för alla grindar. Dina egna ord, ordagrant.",
    journal_empty: "inget bokfört denna session",
    repeated: "En rättelse har återkommit",
    repeated_note: "Två gånger är ett systematiskt fel i agenten, inte ett undantag.",

    honest_h: "Ärlig status",
    honest_1: "<b>Detta är en demomodell.</b> Linjär regression på två drivare, valda " +
      "så att reglagets svar blir jämnt och uppdelningen exakt — inte " +
      "produktionsensemblen, vars vikter sattes av hold-out-backtest. Den är mindre " +
      "träffsäker, och siffran vid varje segment säger hur mycket.",
    honest_2: "<b>Ingen språkmodell körs någonstans i denna pilot.</b> Noll tokens, " +
      "ingen API-nyckel, inget nätanrop. P1:s research är ett fryst urval och " +
      "kapitlet byggs av en deterministisk mall, inte av P3:s skribent.",
    honest_3: "<b>Vad den inte visar:</b> att researchagenten fungerar obevakad, att " +
      "lärandeslingan sluts, att kedjan bär ett andra land, eller att något av det " +
      "körs när laptopen är avstängd.",

    ov_h: "Överskrivning", ov_sub:
      "Skälet bevaras ordagrant och agenten läser det före nästa runda. " +
      "En parafras är redan en tolkning.",
    ov_agent: "agenten föreslog", ov_yours: "ditt värde",
    ov_ph: "Varför? Med dina egna ord.",
    ov_keep: "Agentens värde behålls vid sidan av ditt, så att en senare runda kan " +
      "mäta vilket som låg närmast.",
    ov_commit: "Bokför överskrivning", cancel: "Avbryt", close: "Stäng",
    committed: "Journalfört ordagrant. Agenten läser detta före nästa runda.",
    need_reason: "Ett skäl krävs — det är designen, inte en formulärvalidering.",
    no_quote: "Inget ordagrant citat har förts in i piloten från källdokumentet. " +
      "Produktionskedjan kräver ett innan ett tal får användas — ett tal måste vara " +
      "TRYCKT, och citatet måste kunna återfinnas ord för ord. Att visa ett påhittat " +
      "citat här skulle upphäva just den kontroll panelen finns för att visa.",
    efter_note: "hittat i filen själv, inte inskrivet här",
    institutions: "Institutioner", guard: "värn",
    no_bounds: "inga hårda gränser deklarerade",
    declared_in_config: "deklarerat i konfigurationen",
    not_used: "Används inte av modellen.",
  },
};
