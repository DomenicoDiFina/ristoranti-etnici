"""Tassonomia cucine: continente -> area -> cucina, con tag OSM e tipi Google Places."""

CONTINENTS = {
    'asia':     {'name': 'Asia',          'color': '#ff6b6b'},
    'mo':       {'name': 'Medio Oriente', 'color': '#ffa94d'},
    'africa':   {'name': 'Africa',        'color': '#ffd43b'},
    'americhe': {'name': 'Americhe',      'color': '#38d9a9'},
    'europa':   {'name': 'Europa',        'color': '#4dabf7'},
    'oceania':  {'name': 'Oceania',       'color': '#b197fc'},
}

# (cucina, continente, area, bandiera, tag OSM, tipi Google)
_ROWS = [
    ('Cinese', 'asia', 'Asia orientale', '🇨🇳',
     'chinese cinese sichuan hong_kong dim_sum chinese_dumplings dumpling dumplings baozi hot_pot hotpot',
     'chinese_restaurant cantonese_restaurant dim_sum_restaurant dumpling_restaurant hot_pot_restaurant chinese_noodle_restaurant'),
    ('Giapponese', 'asia', 'Asia orientale', '🇯🇵',
     'japanese sushi ramen mochi edamame',
     'japanese_restaurant sushi_restaurant ramen_restaurant japanese_curry_restaurant japanese_izakaya_restaurant '
     'tonkatsu_restaurant yakiniku_restaurant yakitori_restaurant'),
    ('Coreana', 'asia', 'Asia orientale', '🇰🇷', 'korean corean korean_bbq', 'korean_restaurant korean_barbecue_restaurant'),
    ('Taiwanese', 'asia', 'Asia orientale', '🇹🇼', 'taiwanese bubble_tea', 'taiwanese_restaurant'),
    ('Mongola', 'asia', 'Asia orientale', '🇲🇳', 'mongolian', 'mongolian_barbecue_restaurant'),
    ('Asiatica (mista)', 'asia', 'Asia orientale', '🥢', 'asian oriental noodle noodles',
     'asian_restaurant asian_fusion_restaurant noodle_shop'),
    ('Thailandese', 'asia', 'Sud-est asiatico', '🇹🇭', 'thai', 'thai_restaurant'),
    ('Vietnamita', 'asia', 'Sud-est asiatico', '🇻🇳', 'vietnamese', 'vietnamese_restaurant'),
    ('Filippina', 'asia', 'Sud-est asiatico', '🇵🇭', 'filipino', 'filipino_restaurant'),
    ('Indonesiana', 'asia', 'Sud-est asiatico', '🇮🇩', 'indonesian', 'indonesian_restaurant'),
    ('Malese', 'asia', 'Sud-est asiatico', '🇲🇾', 'malaysian', 'malaysian_restaurant'),
    ('Birmana', 'asia', 'Sud-est asiatico', '🇲🇲', 'burmese', 'burmese_restaurant'),
    ('Cambogiana', 'asia', 'Sud-est asiatico', '🇰🇭', 'cambodian', 'cambodian_restaurant'),
    ('Indiana', 'asia', 'Subcontinente indiano', '🇮🇳', 'indian',
     'indian_restaurant north_indian_restaurant south_indian_restaurant'),
    ('Pakistana', 'asia', 'Subcontinente indiano', '🇵🇰', 'pakistani', 'pakistani_restaurant'),
    ('Srilankese', 'asia', 'Subcontinente indiano', '🇱🇰', 'sri_lankan srilankan singalese', 'sri_lankan_restaurant'),
    ('Bengalese', 'asia', 'Subcontinente indiano', '🇧🇩', 'bangladeshi', 'bangladeshi_restaurant'),
    ('Nepalese', 'asia', 'Subcontinente indiano', '🇳🇵', 'nepalese', ''),
    ('Tibetana', 'asia', 'Subcontinente indiano', '🏔️', 'tibetan', 'tibetan_restaurant'),
    ('Afghana', 'asia', 'Asia centrale', '🇦🇫', 'afghan afghani', 'afghani_restaurant'),
    ('Uzbeka', 'asia', 'Asia centrale', '🇺🇿', 'uzbek', ''),
    ('Kirghisa', 'asia', 'Asia centrale', '🇰🇬', 'kyrgyz', ''),

    ('Turca', 'mo', 'Anatolia e Caucaso', '🇹🇷', 'turkish', 'turkish_restaurant'),
    ('Georgiana', 'mo', 'Anatolia e Caucaso', '🇬🇪', 'georgian', ''),
    ('Kebab', 'mo', 'Street food mediorientale', '🥙', 'kebab pizza_kebab shawarma', 'kebab_shop shawarma_restaurant'),
    ('Araba / Mediorientale', 'mo', 'Levante', '🧆', 'arab middle_eastern falafel pita',
     'middle_eastern_restaurant falafel_restaurant'),
    ('Libanese', 'mo', 'Levante', '🇱🇧', 'lebanese', 'lebanese_restaurant'),
    ('Israeliana / Kosher', 'mo', 'Levante', '🇮🇱', 'kosher israeli', 'israeli_restaurant'),
    ('Persiana', 'mo', 'Iran', '🇮🇷', 'persian iranian', 'persian_restaurant'),

    ('Marocchina', 'africa', 'Nord Africa', '🇲🇦', 'moroccan marocchina', 'moroccan_restaurant'),
    ('Egiziana', 'africa', 'Nord Africa', '🇪🇬', 'egyptian', ''),
    ('Tunisina', 'africa', 'Nord Africa', '🇹🇳', 'tunisian', ''),
    ('Eritrea', 'africa', "Corno d'Africa", '🇪🇷', 'eritrean', ''),
    ('Etiope', 'africa', "Corno d'Africa", '🇪🇹', 'ethiopian', 'ethiopian_restaurant'),
    ('Somala', 'africa', "Corno d'Africa", '🇸🇴', 'somali', ''),
    ('Senegalese', 'africa', 'Africa occidentale', '🇸🇳', 'senegalese', ''),
    ('Nigeriana', 'africa', 'Africa occidentale', '🇳🇬', 'nigerian', ''),
    ('Africana (mista)', 'africa', 'Africa subsahariana', '🌍', 'african', 'african_restaurant'),
    ('Mauriziana', 'africa', 'Oceano Indiano', '🇲🇺', 'mauritian', ''),

    ('Americana', 'americhe', 'Nord America', '🇺🇸', 'american diner bagel cajun',
     'american_restaurant cajun_restaurant californian_restaurant soul_food_restaurant southwestern_us_restaurant'),
    ('Messicana', 'americhe', 'Centro America e Caraibi', '🇲🇽', 'mexican tacos tex-mex burrito',
     'mexican_restaurant taco_restaurant burrito_restaurant tex_mex_restaurant'),
    ('Salvadoregna', 'americhe', 'Centro America e Caraibi', '🇸🇻', 'salvadoran salvadorean', ''),
    ('Cubana', 'americhe', 'Centro America e Caraibi', '🇨🇺', 'cuban', 'cuban_restaurant'),
    ('Caraibica', 'americhe', 'Centro America e Caraibi', '🌴', 'caribbean tropical', 'caribbean_restaurant'),
    ('Peruviana', 'americhe', 'Sud America', '🇵🇪', 'peruvian', 'peruvian_restaurant'),
    ('Brasiliana', 'americhe', 'Sud America', '🇧🇷', 'brazilian', 'brazilian_restaurant'),
    ('Argentina', 'americhe', 'Sud America', '🇦🇷', 'argentinian argentine empanada', 'argentinian_restaurant'),
    ('Colombiana', 'americhe', 'Sud America', '🇨🇴', 'colombian', 'colombian_restaurant'),
    ('Cilena', 'americhe', 'Sud America', '🇨🇱', 'chilean', 'chilean_restaurant'),
    ('Ecuadoriana', 'americhe', 'Sud America', '🇪🇨', 'ecuadorian', ''),
    ('Venezuelana', 'americhe', 'Sud America', '🇻🇪', 'venezuelan', ''),
    ('Sudamericana (mista)', 'americhe', 'Sud America', '🌎', 'latin_american latin sudamericana south_american',
     'latin_american_restaurant south_american_restaurant'),

    ('Spagnola', 'europa', 'Europa occidentale', '🇪🇸', 'spanish tapas basque', 'spanish_restaurant tapas_restaurant basque_restaurant'),
    ('Portoghese', 'europa', 'Europa occidentale', '🇵🇹', 'portuguese', 'portuguese_restaurant'),
    ('Francese', 'europa', 'Europa occidentale', '🇫🇷', 'french crepe brasserie', 'french_restaurant'),
    ('Belga', 'europa', 'Europa occidentale', '🇧🇪', 'belgian', 'belgian_restaurant'),
    ('Olandese', 'europa', 'Europa occidentale', '🇳🇱', 'dutch', 'dutch_restaurant'),
    ('Britannica', 'europa', 'Europa occidentale', '🇬🇧', 'fish_and_chips british english',
     'british_restaurant fish_and_chips_restaurant'),
    ('Tedesca', 'europa', 'Europa centrale', '🇩🇪', 'german bavarian pretzel', 'german_restaurant bavarian_restaurant'),
    ('Austriaca', 'europa', 'Europa centrale', '🇦🇹', 'austrian heuriger', 'austrian_restaurant'),
    ('Svizzera', 'europa', 'Europa centrale', '🇨🇭', 'swiss', 'swiss_restaurant fondue_restaurant'),
    ('Ungherese', 'europa', 'Europa centrale', '🇭🇺', 'hungarian', 'hungarian_restaurant'),
    ('Ceca', 'europa', 'Europa centrale', '🇨🇿', 'czech', 'czech_restaurant'),
    ('Scandinava', 'europa', 'Nord Europa', '🇸🇪', 'danish danese swedish norwegian scandinavian',
     'scandinavian_restaurant danish_restaurant'),
    ('Russa', 'europa', 'Europa orientale', '🇷🇺', 'russian', 'russian_restaurant'),
    ('Ucraina', 'europa', 'Europa orientale', '🇺🇦', 'ukrainian', 'ukrainian_restaurant'),
    ('Rumena', 'europa', 'Europa orientale', '🇷🇴', 'romanian', 'romanian_restaurant'),
    ('Polacca', 'europa', 'Europa orientale', '🇵🇱', 'polish', 'polish_restaurant'),
    ('Est europea (mista)', 'europa', 'Europa orientale', '🌐', 'eastern_european', 'eastern_european_restaurant'),
    ('Greca', 'europa', 'Balcani e Grecia', '🇬🇷', 'greek gyros', 'greek_restaurant gyro_restaurant'),
    ('Balcanica', 'europa', 'Balcani e Grecia', '🇷🇸', 'balkan serbian bosnian', ''),
    ('Croata', 'europa', 'Balcani e Grecia', '🇭🇷', 'croatian', 'croatian_restaurant'),

    ('Hawaiana / Poke', 'oceania', 'Pacifico', '🌺', 'hawaiian poke', 'hawaiian_restaurant'),
    ('Australiana', 'oceania', 'Australia', '🇦🇺', 'australian', 'australian_restaurant'),
]

CUISINES = {}   # cucina -> {cont, area, flag}
OSM = {}        # tag OSM -> cucina
GOOGLE = {}     # tipo Google -> cucina
for label, cont, area, flag, osm, google in _ROWS:
    CUISINES[label] = {'cont': cont, 'area': area, 'flag': flag}
    for k in osm.split():
        OSM[k] = label
    for t in google.split():
        GOOGLE[t] = label

# termini di ricerca per il testo libero di Google (solo per tipi molto generici)
QUERY_HINT = {
    'kebab_shop': 'kebab', 'shawarma_restaurant': 'shawarma', 'sushi_restaurant': 'sushi',
    'ramen_restaurant': 'ramen', 'hawaiian_restaurant': 'poke', 'noodle_shop': 'noodles',
}

# specialità mostrate come etichette secondarie
SPECIALS = {
    'sushi': 'Sushi', 'sushi_restaurant': 'Sushi', 'ramen': 'Ramen', 'ramen_restaurant': 'Ramen',
    'dim_sum': 'Dim sum', 'dim_sum_restaurant': 'Dim sum', 'hot_pot': 'Hot pot', 'hotpot': 'Hot pot',
    'hot_pot_restaurant': 'Hot pot', 'korean_bbq': 'BBQ coreano', 'korean_barbecue_restaurant': 'BBQ coreano',
    'bubble_tea': 'Bubble tea', 'tacos': 'Tacos', 'taco_restaurant': 'Tacos', 'tapas': 'Tapas',
    'tapas_restaurant': 'Tapas', 'falafel': 'Falafel', 'falafel_restaurant': 'Falafel', 'poke': 'Poke',
    'sichuan': 'Sichuan', 'dumpling': 'Ravioli', 'dumplings': 'Ravioli', 'chinese_dumplings': 'Ravioli',
    'dumpling_restaurant': 'Ravioli', 'baozi': 'Baozi', 'empanada': 'Empanadas', 'crepe': 'Crêpes',
    'japanese_izakaya_restaurant': 'Izakaya', 'yakitori_restaurant': 'Yakitori', 'yakiniku_restaurant': 'Yakiniku',
    'tonkatsu_restaurant': 'Tonkatsu', 'japanese_curry_restaurant': 'Curry giapponese',
    'burrito_restaurant': 'Burrito', 'shawarma_restaurant': 'Shawarma', 'gyro_restaurant': 'Gyros',
    'fondue_restaurant': 'Fonduta', 'cantonese_restaurant': 'Cantonese',
}
