

- Data source:
- https://www.marktstammdatenregister.de/MaStR

- TODO: there is an API, but the documentation is a bit weird and I think one has to be registered
- 

- download the zip file here: https://www.marktstammdatenregister.de/MaStR/Datendownload
- there is a pdf explaining it: https://www.marktstammdatenregister.de/MaStRHilfe/files/gesamtdatenexport/Dokumentation%20MaStR%20Gesamtdatenexport.pdf
- the zip is quite large (ca 1gb) and when extracted even larger (ca 19gb) hence it is not part of the repo
- TODO: write a unzip command that only extracts the relevant files which are:

```
unzip -j Gesamtdatenexport_20220122__7deb41eb7fee404f8177517ba2978030.zip "EinheitenStromSpeicher_*" "AnlagenStromSpeicher_*" "Marktakteure_*" -d extracted
unzip -j Gesamtdatenexport_20220122__7deb41eb7fee404f8177517ba2978030.zip "Marktakteure_*" -d extracted

```

  - `EinheitenStromSpeicher_1.xml` (files 1-5) - contains all basic info
  - `AnlagenStromSpeicher_1.xml` (files 1-5) - contains mwh info

- TODO `Marktakteure_20.xml` (1-22) - can be used to look up the  ABR932212103470 numbers

- for now filtering on th mw filed if it is more or equal than 10mw. 
- TODO: maybe change the filter to 10mwh (but thats in the other field)


An example XML is:

```xml

<EinheitenStromSpeicher>
    <!-- detail page: https://www.marktstammdatenregister.de/MaStR/Einheit/Detail/IndexOeffentlich/3408294#technischedaten -->
	<EinheitStromSpeicher>
		<EinheitMastrNummer>SEE999646120152</EinheitMastrNummer>
		<DatumLetzteAktualisierung>2021-05-05T18:56:42.2974294</DatumLetzteAktualisierung>
		<LokationMaStRNummer>SEL942540862352</LokationMaStRNummer>
		<NetzbetreiberpruefungStatus>1</NetzbetreiberpruefungStatus>
		<NetzbetreiberpruefungDatum>2021-05-06</NetzbetreiberpruefungDatum>
		<AnlagenbetreiberMastrNummer>ABR981376799364</AnlagenbetreiberMastrNummer>
		<Land>84</Land>
		<Bundesland>1403</Bundesland>
		<Landkreis>Fürstenfeldbruck</Landkreis>
		<Gemeinde>Eichenau</Gemeinde>
		<Gemeindeschluessel>09179118</Gemeindeschluessel>
		<Postleitzahl>82223</Postleitzahl>
		<Ort>Eichenau</Ort>
		<Registrierungsdatum>2020-09-07</Registrierungsdatum>
		<Inbetriebnahmedatum>2020-09-03</Inbetriebnahmedatum>
		<EinheitSystemstatus>472</EinheitSystemstatus>
		<EinheitBetriebsstatus>35</EinheitBetriebsstatus>
		<NichtVorhandenInMigriertenEinheiten>0</NichtVorhandenInMigriertenEinheiten>
		<NameStromerzeugungseinheit>Batterie</NameStromerzeugungseinheit>
		<Weic_nv>0</Weic_nv>
		<Kraftwerksnummer_nv>0</Kraftwerksnummer_nv>
		<Energietraeger>2496</Energietraeger>
		<Bruttoleistung>4.600</Bruttoleistung>
		<Nettonennleistung>4.600</Nettonennleistung>
		<FernsteuerbarkeitNb>0</FernsteuerbarkeitNb>
		<Einspeisungsart>689</Einspeisungsart>
		<AcDcKoppelung>693</AcDcKoppelung>
        <!-- 727 - is Lithium Batterie on the detail page -->
		<Batterietechnologie>727</Batterietechnologie>
		<Notstromaggregat>0</Notstromaggregat>
		<ZugeordnenteWirkleistungWechselrichter>8.200</ZugeordnenteWirkleistungWechselrichter>
		<!-- the number that links to the anlagen files -->
        <SpeMastrNummer>SSE972588961854</SpeMastrNummer>
		<EegMaStRNummer>EEG918883901706</EegMaStRNummer>
		<EegAnlagentyp>8</EegAnlagentyp>
        <!-- TODO: find out what that means, might be just the battery -->
		<Technologie>524</Technologie>
	</EinheitStromSpeicher>
	<EinheitStromSpeicher>
		<EinheitMastrNummer>SEE999646661129</EinheitMastrNummer>
		<DatumLetzteAktualisierung>2021-11-01T07:26:23.7840473</DatumLetzteAktualisierung>
		<LokationMaStRNummer>SEL970216017713</LokationMaStRNummer>


<AnlagenStromSpeicher>
    <AnlageStromSpeicher>
        <MaStRNummer>SSE999679462663</MaStRNummer>
        <Registrierungsdatum>2021-05-19</Registrierungsdatum>
        <DatumLetzteAktualisierung>2021-08-16T19:34:59.1632215</DatumLetzteAktualisierung>
        <NutzbareSpeicherkapazitaet>10.200</NutzbareSpeicherkapazitaet>
        <VerknuepfteEinheitenMaStRNummern>SEE952052191000</VerknuepfteEinheitenMaStRNummern>
        <AnlageBetriebsstatus>35</AnlageBetriebsstatus>
    </AnlageStromSpeicher>
    <AnlageStromSpeicher>
        <MaStRNummer>SSE999679476417</MaStRNummer>


<Marktakteure>
    <Marktakteur>
        <MastrNummer>ABR999811578986</MastrNummer>
        <Personenart>518</Personenart>
        <Marktfunktion>2</Marktfunktion>
        <RegistergerichtAusland></RegistergerichtAusland>
        <Registernummer></Registernummer>
    </Marktakteur>
    <Marktakteur>
        <MastrNummer>ABR999811635924</MastrNummer>
        <DatumLetzeAktualisierung>2019-12-02T09:16:46.3179167</DatumLetzeAktualisierung>
        <Personenart>517</Personenart>
        <Firmenname>Vigotec GmbH</Firmenname>
        <Marktfunktion>2</Marktfunktion>
        <Rechtsform>429</Rechtsform>
        <Land>84</Land>
        <Strasse>Äußere Frühlingstraße</Strasse>
        <Hausnummer>28</Hausnummer>
        <Hausnummer_nv>0</Hausnummer_nv>
        <Postleitzahl>94315</Postleitzahl>
        <Ort>Straubing</Ort>
        <Bundesland>335</Bundesland>
        <Nuts2>Straubing, kreisfreie Stadt</Nuts2>
        <Email>info@vigotec.de</Email>
        <Fax_nv>1</Fax_nv>
        <Webseite_nv>1</Webseite_nv>
        <Registergericht>1031</Registergericht>
        <RegistergerichtAusland></RegistergerichtAusland>
        <Registernummer>11636</Registernummer>
        <Taetigkeitsbeginn>2011-10-26</Taetigkeitsbeginn>
        <AcerCode_nv>1</AcerCode_nv>
        <Umsatzsteueridentifikationsnummer>DE260216386</Umsatzsteueridentifikationsnummer>
        <Umsatzsteueridentifikationsnummer_nv>0</Umsatzsteueridentifikationsnummer_nv>
        <BundesnetzagenturBetriebsnummer></BundesnetzagenturBetriebsnummer>
        <BundesnetzagenturBetriebsnummer_nv>0</BundesnetzagenturBetriebsnummer_nv>
        <HausnummerAnZustelladresse_nv>0</HausnummerAnZustelladresse_nv>
        <Kmu>0</Kmu>
        <RegistrierungsdatumMarktakteur>2019-12-02T09:16:45.7848096</RegistrierungsdatumMarktakteur>
    </Marktakteur>


```


```json
// json sample of elverlingslesn
 {'AcDcKoppelung': '694',
  'AnlagenbetreiberMastrNummer': 'ABR922907721966',
  'AnschlussAnHoechstOderHochSpannung': '0',
  'Batterietechnologie': '727',
  'Breitengrad': '51.274860',
  'Bruttoleistung': '17080.000',
  'Bundesland': '1409',
  'DatumLetzteAktualisierung': '2021-02-15T12:47:02.2298795',
  'EegAnlagentyp': '8',
  'EinheitBetriebsstatus': '35',
  'EinheitMastrNummer': 'SEE966091400436',
  'EinheitSystemstatus': '472',
  'Einsatzverantwortlicher': '9903097000002',
  'Einspeisungsart': '688',
  'Energietraeger': '2496',
  'FernsteuerbarkeitDr': '0',
  'FernsteuerbarkeitDv': '0',
  'FernsteuerbarkeitNb': '1',
  'Gemeinde': 'Werdohl',
  'Gemeindeschluessel': '05962060',
  'Hausnummer': '1',
  'HausnummerNichtGefunden': '1',
  'Hausnummer_nv': '0',
  'Inbetriebnahmedatum': '2017-07-01',
  'Kraftwerksnummer_nv': '1',
  // for the units that have coordinates, it is there...
  'Laengengrad': '7.704284',
  'Land': '84',
  'Landkreis': 'Märkischer Kreis',
  'LokationMaStRNummer': 'SEL990520260384',
  'NameStromerzeugungseinheit': 'Q_ESS_Elverlingsen',
  'Nettonennleistung': '17080.000',
  'NetzbetreiberpruefungDatum': '2021-05-26',
  'NetzbetreiberpruefungStatus': '0',
  'NichtVorhandenInMigriertenEinheiten': '0',
  'Notstromaggregat': '0',
  'Ort': 'Werdohl',
  'Postleitzahl': '58791',
  'Registrierungsdatum': '2019-12-17',
  'SpeMastrNummer': 'SSE987360535918',
  'Strasse': 'Auf der Mark',
  'StrasseNichtGefunden': '1',
  'Technologie': '524',
  'Weic_nv': '1',
  'ZugeordnenteWirkleistungWechselrichter': '17080.000'},



```

# small battery analysis

Some other resources about the small battery market 
- https://www.pv-magazine.de/2022/08/23/monitoring-bericht-photovoltaik-speicherfoerderung-in-baden-wuerttemberg-fuehrt-zu-zahlreichen-zusaetzlichen-anlagen/

- The development of battery storage systems in Germany – A market review (status 2022)
- https://arxiv.org/ftp/arxiv/papers/2203/2203.06762.pdf
  - the define a HSS - home storage system to be less than 30kwh
  - will use the same definition here for small batteries



