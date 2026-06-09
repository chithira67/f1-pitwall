# f1pitwall/app/components/driver_images.py
"""
Driver headshot URLs from the official F1 website CDN.
Falls back to a placeholder if the driver isn't found.
"""

# Official F1 website headshot URLs
# Format: https://www.formula1.com/content/dam/fom-website/drivers/
#         {FIRST_LETTER}/{CODE_FULL}/{CODE_FULL}.png
# These are publicly accessible and update each season.

DRIVER_IMAGES: dict[str, str] = {
    # 2024/2025 grid
    "VER": "https://www.formula1.com/content/dam/fom-website/drivers/M/MAXVER01_Max_Verstappen/maxver01.png",
    "NOR": "https://www.formula1.com/content/dam/fom-website/drivers/L/LANNOR01_Lando_Norris/lannor01.png",
    "LEC": "https://www.formula1.com/content/dam/fom-website/drivers/C/CHALEC01_Charles_Leclerc/chalec01.png",
    "PIA": "https://www.formula1.com/content/dam/fom-website/drivers/O/OSCPIA01_Oscar_Piastri/oscpia01.png",
    "SAI": "https://www.formula1.com/content/dam/fom-website/drivers/C/CARSAI01_Carlos_Sainz/carsai01.png",
    "RUS": "https://www.formula1.com/content/dam/fom-website/drivers/G/GEORUS01_George_Russell/georus01.png",
    "HAM": "https://www.formula1.com/content/dam/fom-website/drivers/L/LEWHAM01_Lewis_Hamilton/lewham01.png",
    "ANT": "https://www.formula1.com/content/dam/fom-website/drivers/A/ANDANT01_Andrea_Kimi_Antonelli/andant01.png",
    "ALO": "https://www.formula1.com/content/dam/fom-website/drivers/F/FERALO01_Fernando_Alonso/feralo01.png",
    "STR": "https://www.formula1.com/content/dam/fom-website/drivers/L/LANSTR01_Lance_Stroll/lanstr01.png",
    "TSU": "https://www.formula1.com/content/dam/fom-website/drivers/Y/YUKTSU01_Yuki_Tsunoda/yuktsu01.png",
    "LAW": "https://www.formula1.com/content/dam/fom-website/drivers/L/LIALAW01_Liam_Lawson/lialaw01.png",
    "ALB": "https://www.formula1.com/content/dam/fom-website/drivers/A/ALEALB01_Alexander_Albon/alealb01.png",
    "SAR": "https://www.formula1.com/content/dam/fom-website/drivers/L/LOGSAR01_Logan_Sargeant/logsar01.png",
    "COL": "https://www.formula1.com/content/dam/fom-website/drivers/F/FRACOL01_Franco_Colapinto/fracol01.png",
    "HUL": "https://www.formula1.com/content/dam/fom-website/drivers/N/NICHUL01_Nico_Hulkenberg/nichul01.png",
    "BEA": "https://www.formula1.com/content/dam/fom-website/drivers/O/OLIBEA01_Oliver_Bearman/olibea01.png",
    "OCO": "https://www.formula1.com/content/dam/fom-website/drivers/E/ESTOCO01_Esteban_Ocon/estoco01.png",
    "GAS": "https://www.formula1.com/content/dam/fom-website/drivers/P/PIEGAS01_Pierre_Gasly/piegas01.png",
    "DOO": "https://www.formula1.com/content/dam/fom-website/drivers/J/JACDOO01_Jack_Doohan/jacdoo01.png",
    "HAD": "https://www.formula1.com/content/dam/fom-website/drivers/I/ISAHAD01_Isack_Hadjar/isahad01.png",
    "MAG": "https://www.formula1.com/content/dam/fom-website/drivers/K/KEVMAG01_Kevin_Magnussen/kevmag01.png",
    "BOT": "https://www.formula1.com/content/dam/fom-website/drivers/V/VALBOT01_Valtteri_Bottas/valbot01.png",
    "ZHO": "https://www.formula1.com/content/dam/fom-website/drivers/G/GUAZHO01_Guanyu_Zhou/guazho01.png",
    "RIC": "https://www.formula1.com/content/dam/fom-website/drivers/D/DANRIC01_Daniel_Ricciardo/danric01.png",
    "PER": "https://www.formula1.com/content/dam/fom-website/drivers/S/SERPER01_Sergio_Perez/serper01.png",
    "BOR": "https://www.formula1.com/content/dam/fom-website/drivers/G/GABBAR01_Gabriel_Bortoleto/gabbar01.png",
}

PLACEHOLDER = "https://www.formula1.com/content/dam/fom-website/drivers/S/SILHOU_Silhouette/silhou.png"


def get_driver_image(driver_code: str) -> str:
    """Return headshot URL for a driver code. Falls back to silhouette."""
    return DRIVER_IMAGES.get(driver_code.upper(), PLACEHOLDER)