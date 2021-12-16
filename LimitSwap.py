# -*- coding: utf-8 -*-
from web3 import Web3
from time import sleep, time
import json
from decimal import Decimal
import os
import web3
from web3.exceptions import ABIFunctionNotFound, TransactionNotFound, BadFunctionCallOutput
import logging
from datetime import datetime
import sys
import requests
import cryptocode, re, pwinput
import argparse
import signal

# DEVELOPER CONSIDERATIONS
#
# USER INTERACTION - Do not depend on user interaction. If you develop a setting that is going to require
#    user interaction while the bot is running, warn the user before hand. Accept a value before the check
#    for liquidity, and provide a command line flag. Basically, provide ways for the bot to continue it's
#    entire process from buying all the way to selling multiple positions and multiple pairs with zero user
#    interaction.
#
# HANDLING NEW ENTRIES IN settings.json - When adding a new configuration item in settings.json be sure to
#    review comment "COMMAND LINE ARGUMENTS" and the functions load_settings_file and save_settings_file.
#    Do not assume a user has changed their settings.json file to work with the new version, your additions
#    should be backwards compatible and have safe default values if possible
#
# HANDLING NEW ENTRIES IN tokens.json - When adding a new configuration item in tokens.json be sure to
#    review comment "COMMAND LINE ARGUMENTS" and the functions load_settings_file and save_settings_file
#    Do not assume a user has changed their tokens.json file to work with the new version, your additions
#    should be backwards compatible and have safe default values if possible


# initialization of number of failed transactions
failedtransactionsamount = 0

# color styles
class style():  # Class of different text colours - default is white
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'
    INFO = '\033[36m'
    DEBUG = '\033[35m'

# Function to cleanly exit on SIGINT
def signal_handler(sig, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def timestamp():
    timestamp = time()
    dt_object = datetime.fromtimestamp(timestamp)
    return dt_object


#
# START - COMMAND LINE ARGUMENTS
#
parser = argparse.ArgumentParser()

# USER COMMAND LINE ARGUMENTS
parser.add_argument("-p", "--password", type=str,
                    help="Password to decrypt private keys (WARNING: your password could be saved in your command prompt history)")
parser.add_argument("-s", "--settings", type=str, help="Specify the file to user for settings (default: settings.json)",
                    default="./settings.json")
parser.add_argument("-t", "--tokens", type=str,
                    help="Specify the file to use for tokens to trade (default: tokens.json)", default="./tokens.json")
parser.add_argument("-v", "--verbose", action='store_true', help="Print detailed messages to stdout")

# DEVELOPER COMMAND LINE ARGUMENTS
# --dev - general argument for developer options
# --sim_buy tx - simulates the buying process, you must provide a transaction of a purchase of the token
# --sim_sell tx - simulates the buying process, you must provide a transaction of a purchase of the token
parser.add_argument("--dev", action='store_true', help=argparse.SUPPRESS)
parser.add_argument("--sim_buy", type=str, help=argparse.SUPPRESS)
parser.add_argument("--sim_sell", type=str, help=argparse.SUPPRESS)
parser.add_argument("--debug", action='store_true', help=argparse.SUPPRESS)

command_line_args = parser.parse_args()
#
# END - COMMAND LINE ARGUMENTS
#


def printt(*print_args):
    # Function: printt
    # ----------------------------
    # provides normal print() functionality but also prints our timestamp
    #
    # print_args - normal arguments that would be passed to the print() function
    #
    # returns: nothing

    print(timestamp(), ' '.join(map(str, print_args)))


def printt_v(*print_args):
    # Function: printt
    # ----------------------------
    # provides normal print() functionality but also prints our timestamp and pays attention to user set verbosity.
    #
    # print_args - normal arguments that would be passed to the print() function
    #
    # returns: nothing

    if command_line_args.verbose == True:
        print(timestamp(), ' '.join(map(str, print_args)))


def printt_err(*print_args, write_to_log=True):
    # Function: printt_err
    # --------------------
    # provides normal print() functionality but also prints our timestamp and the text highlighted to display an error
    # 
    # print_args - normal arguments that would be passed to the print() function
    # write_to_log - wether or not to write the same text to the log file
    #
    # returns: nothing

    print(timestamp(), " ", style.RED, ' '.join(map(str,print_args)), style.RESET, sep="")
    
    if write_to_log == True:
        logging.info(' '.join(map(str,print_args)))


def printt_warn(*print_args):
    # Function: printt_warn
    # --------------------
    # provides normal print() functionality but also prints our timestamp and the text highlighted to display a warning
    #
    # print_args - normal arguments that would be passed to the print() function
    #
    # returns: nothing

    print(timestamp(), " ", style.YELLOW, ' '.join(map(str,print_args)), style.RESET, sep="")


def printt_ok(*print_args):
    # Function: printt_ok
    # --------------------
    # provides normal print() functionality but also prints our timestamp and the text highlighted to display an OK text
    #
    # returns: nothing

    print(timestamp(), " ", style.GREEN, ' '.join(map(str, print_args)), style.RESET, sep="")


def printt_info(*print_args):
    # Function: printt_info
    # --------------------
    # provides normal print() functionality but also prints our timestamp and the text highlighted to display an INFO text in yellow
    #
    # returns: nothing

    print(timestamp(), " ", style.BLUE, ' '.join(map(str, print_args)), style.RESET, sep="")

def printt_debug(*print_args):
    # Function: printt_warn
    # --------------------
    # provides normal print() functionality but also prints our timestamp and the text highlighted to display a warning
    #
    # print_args - normal arguments that would be passed to the print() function
    #
    # returns: nothing

    if command_line_args.debug == True:
        print(timestamp(), " ", style.DEBUG, ' '.join(map(str,print_args)), style.RESET, sep="")


def load_settings_file(settings_path, load_message=True):
    # Function: load_settings_file
    # ----------------------------
    # loads the settings file defined by command_line_args.settings, sets sane defaults if variables aren't found in settings file
    # exits with an error message if necessary variables are not found in the settings files
    #
    # settings_path = the path of the file to load settings from
    #
    # returns: a dictionary with the settings from the file loaded

    if load_message == True:
        print(timestamp(), "Loading settings from", settings_path)

    f = open(settings_path, )
    settings = json.load(f)[0]
    f.close()

    default_false_settings =[
        'UNLIMITEDSLIPPAGE',
        'USECUSTOMNODE'
    ]

    default_true_settings = [
        'PREAPPROVE'
    ]

    # These settings must be defined by the user and we will lower() them
    required_user_settings = [
        'EXCHANGE'
    ]

    for default_false in default_false_settings:
        if default_false not in settings:
            printt_v(default_false, "not found in settings configuration file, settings a default value of false.")
            settings[default_false] = "false"
        else:
            settings[default_false] = settings[default_false].lower()

    for default_true in default_true_settings:
        if default_true not in settings:
            printt_v(default_true, "not found in settings configuration file, settings a default value of true.")
            settings[default_true] = "true"
        else:
            settings[default_true] = settings[default_true].lower()

    # Keys that must be set
    for required_setting in required_user_settings:
        if required_setting not in settings:
            printt_err(required_setting, "not found in settings configuration file.")
            exit(-1)
        else:
            settings[required_setting] = settings[required_setting].lower()

    return settings


def load_tokens_file(tokens_path, load_message=True):
    # Function: load_tokens_File
    # ----------------------------
    # loads the token definition file defined by command_line_args.settings, sets sane defaults if variables aren't found in settings file
    # exits with an error message if necessary variables are not found in the settings files
    #
    # tokens_path: the path of the file to load tokens from
    #
    # returns: a dictionary with the settings from the file loaded

    if load_message == True:
        print(timestamp(), "Loading tokens from", tokens_path)

    s = open(tokens_path, )
    tokens = json.load(s)
    s.close()

    required_user_settings =[
        'ADDRESS',
        'BUYAMOUNTINBASE',
        'BUYPRICEINBASE',
        'SELLPRICEINBASE'
    ]

    default_false_settings = [
        'ENABLED',
        'LIQUIDITYCHECK',
        'LIQUIDITYINNATIVETOKEN',
        'USECUSTOMBASEPAIR',
        'HASFEES',
        'RUGDOC_CHECK'
    ]

    default_value_settings = {
        'SLIPPAGE' : 49,
        'MAXTOKENS' : 0,
        'MOONBAG' : 0,
        'SELLAMOUNTINTOKENS' : 'all',
        'GAS' : 20,
        'BOOSTPERCENT' : 50,
        'GASLIMIT' : 1000000,
        'BUYAFTER_XXX_SECONDS' : 0,
        'MAX_FAILED_TRANSACTIONS_IN_A_ROW' : 0,
        'STOPLOSSPRICEINBASE' : 0
    }

    # There are values that we will set internally. They must all begin with _
    # _LIQUIDITY_CHECKED - false if we have yet to check liquidity for this token
    # _INFORMED_SELL - set to true when we've already informed the user that we're selling this position
    program_defined_values = {
        '_LIQUIDITY_READY' : False,
        '_LIQUIDITY_CHECKED' : False,
        '_INFORMED_SELL' : False,
        '_REACHED_MAX_TOKENS' : True,
        '_ACTUAL_BUY_PRICE' : 0
    }

    for token in tokens:

        # Keys that must be set
        for required_key in required_user_settings:
            if required_key not in token:
                printt_err (required_key, "not found in configuration file in configuration for to token", token['SYMBOL'])
                exit (-1)

        for default_false in default_false_settings:
            if default_false not in token:
                printt_v(default_false, "not found in configuration file in configuration for to token",
                         token['SYMBOL'], "setting a default value of false")
                token[default_false] = "false"
            else:
                token[default_false] = token[default_false].lower()

        for default_key in default_value_settings:
            if default_key not in token:
                printt_v (default_key , "not found in configuration file in configuration for to token", token['SYMBOL'], "setting a value of", default_value_settings[default_key])
                token[default_key] = default_value_settings[default_key]
            elif default_key == 'SELLAMOUNTINTOKENS':
                default_value_settings[default_key] = default_value_settings[default_key].lower()

        if next(iter(program_defined_values)) not in token:
            for value in program_defined_values:
                token[value] = program_defined_values[value]

    return tokens


def build_token_list(tokens, all_pairs=False):
    # Function: build_token_pair_list
    # ----------------------------
    # takes our tokens object formated as an array of dicts and returns an array of trading pairs
    #
    # tokens: array of dicts representing the tokens to trade in the format absorbed by load_tokens_file
    # all_pairs: If False (default) returns all enabled pairs - if True returns both enabled and disabled pairs
    #
    # returns: an array of all SYMBOLS we are trading

    token_list = ""

    for token in tokens:
        if all_pairs == True or token["ENABLED"] == 'true':
            if token_list != "":
                token_list = token_list + " "
            token_list = token_list + token['SYMBOL']

    return token_list
  
  
"""""""""""""""""""""""""""
//PRELOAD
"""""""""""""""""""""""""""
print(timestamp(), "Preloading Data")
settings = load_settings_file(command_line_args.settings)

directory = './abi/'
filename = "standard.json"
file_path = os.path.join(directory, filename)
with open(file_path) as json_file:
    standardAbi = json.load(json_file)

directory = './abi/'
filename = "lp.json"
file_path = os.path.join(directory, filename)
with open(file_path) as json_file:
    lpAbi = json.load(json_file)

directory = './abi/'
filename = "router.json"
file_path = os.path.join(directory, filename)
with open(file_path) as json_file:
    routerAbi = json.load(json_file)

directory = './abi/'
filename = "factory2.json"
file_path = os.path.join(directory, filename)
with open(file_path) as json_file:
    factoryAbi = json.load(json_file)

directory = './abi/'
filename = "koffee.json"
file_path = os.path.join(directory, filename)
with open(file_path) as json_file:
    koffeeAbi = json.load(json_file)

directory = './abi/'
filename = "pangolin.json"
file_path = os.path.join(directory, filename)
with open(file_path) as json_file:
    pangolinAbi = json.load(json_file)

directory = './abi/'
filename = "joeRouter.json"
file_path = os.path.join(directory, filename)
with open(file_path) as json_file:
    joeRouter = json.load(json_file)

"""""""""""""""""""""""""""
//ERROR LOGGING
"""""""""""""""""""""""""""
os.makedirs('./logs', exist_ok=True)

if not os.path.exists('./logs/errors.log'):
    open('./logs/errors.log', 'w').close()

if not os.path.exists('./logs/exceptions.log'):
    open('./logs/exceptions.log', 'w').close()

log_format = '%(levelname)s: %(asctime)s %(message)s'
logging.basicConfig(filename='./logs/errors.log',
                    level=logging.INFO,
                    format=log_format)

logger1 = logging.getLogger('1')
logger1.addHandler(logging.FileHandler('./logs/exceptions.log'))

logging.info("*************************************************************************************")
logging.info("For Help & To Learn More About how the bot works please visit our wiki here:")
logging.info("https://cryptognome.gitbook.io/limitswap/")
logging.info("*************************************************************************************")

"""""""""""""""""""""""""""
//NETWORKS SELECT
"""""""""""""""""""""""""""

if settings['EXCHANGE'] == 'pancakeswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
        print(timestamp(), 'Using custom node.')
    else:
        my_provider = "https://bsc-dataseed4.defibit.io"

    if not my_provider:
        print(timestamp(), 'Custom node empty. Exiting')
        exit(1)

    if my_provider[0].lower() == 'h':
        print(timestamp(), 'Using HTTPProvider')
        client = Web3(Web3.HTTPProvider(my_provider))
    elif my_provider[0].lower() == 'w':
        print(timestamp(), 'Using WebsocketProvider')
        client = Web3(Web3.WebsocketProvider(my_provider))
    else:
        print(timestamp(), 'Using IPCProvider')
        client = Web3(Web3.IPCProvider(my_provider))

    print(timestamp(), "Binance Smart Chain Connected =", client.isConnected())
    print(timestamp(), "Loading Smart Contracts...")

    if settings['EXCHANGEVERSION'] == "1":
        routerAddress = Web3.toChecksumAddress("0x05fF2B0DB69458A0750badebc4f9e13aDd608C7F")
        factoryAddress = Web3.toChecksumAddress("0xbcfccbde45ce874adcb698cc183debcf17952812")
    elif settings['EXCHANGEVERSION'] == "2":
        routerAddress = Web3.toChecksumAddress("0x10ED43C718714eb63d5aA57B78B54704E256024E")
        factoryAddress = Web3.toChecksumAddress("0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73")

    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
    base_symbol = "BNB"
    rugdocchain = '&chain=bsc'
    modified = False

if settings['EXCHANGE'] == 'traderjoe':

    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://api.avax.network/ext/bc/C/rpc"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "AVAX Smart Chain Connected =", client.isConnected())
    print(timestamp(), "Loading Smart Contracts...")

    routerAddress = Web3.toChecksumAddress("0x60aE616a2155Ee3d9A68541Ba4544862310933d4")
    factoryAddress = Web3.toChecksumAddress("0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10")

    routerContract = client.eth.contract(address=routerAddress, abi=joeRouter)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7")
    base_symbol = "AVAX"
    rugdocchain = '&chain=avax'
    modified = True

elif settings['EXCHANGE'] == 'pinkswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
        print(timestamp(), 'Using custom node.')
    else:
        my_provider = "https://bsc-dataseed4.defibit.io"

    if not my_provider:
        print(timestamp(), 'Custom node empty. Exiting')
        exit(1)

    if my_provider[0].lower() == 'h':
        print(timestamp(), 'Using HTTPProvider')
        client = Web3(Web3.HTTPProvider(my_provider))
    elif my_provider[0].lower() == 'w':
        print(timestamp(), 'Using WebsocketProvider')
        client = Web3(Web3.WebsocketProvider(my_provider))
    else:
        print(timestamp(), 'Using IPCProvider')
        client = Web3(Web3.IPCProvider(my_provider))

    print(timestamp(), "Binance Smart Chain Connected =", client.isConnected())
    print(timestamp(), "Loading PinkSwap Smart Contracts...")

    routerAddress = Web3.toChecksumAddress("0x319EF69a98c8E8aAB36Aea561Daba0Bf3D0fa3ac")
    factoryAddress = Web3.toChecksumAddress("0x7d2ce25c28334e40f37b2a068ec8d5a59f11ea54")

    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)

    weth = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
    base_symbol = "BNB"
    rugdocchain = '&chain=bsc'
    modified = False

elif settings['EXCHANGE'] == 'biswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
        print(timestamp(), 'Using custom node.')
    else:
        my_provider = "https://bsc-dataseed4.defibit.io"

    if not my_provider:
        print(timestamp(), 'Custom node empty. Exiting')
        exit(1)

    if my_provider[0].lower() == 'h':
        print(timestamp(), 'Using HTTPProvider')
        client = Web3(Web3.HTTPProvider(my_provider))
    elif my_provider[0].lower() == 'w':
        print(timestamp(), 'Using WebsocketProvider')
        client = Web3(Web3.WebsocketProvider(my_provider))
    else:
        print(timestamp(), 'Using IPCProvider')
        client = Web3(Web3.IPCProvider(my_provider))

    print(timestamp(), "Binance Smart Chain Connected =", client.isConnected())
    print(timestamp(), "Loading PinkSwap Smart Contracts...")

    routerAddress = Web3.toChecksumAddress("0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8")
    factoryAddress = Web3.toChecksumAddress("0x858E3312ed3A876947EA49d572A7C42DE08af7EE")

    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)

    weth = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
    base_symbol = "BNB"
    rugdocchain = '&chain=bsc'
    modified = False

elif settings['EXCHANGE'] == 'apeswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://bsc-dataseed4.defibit.io"

    client = Web3(Web3.HTTPProvider(my_provider))

    print(timestamp(), "Binance Smart Chain Connected =", client.isConnected())
    print(timestamp(), "Loading ApeSwap Smart Contracts...")

    routerAddress = Web3.toChecksumAddress("0xcF0feBd3f17CEf5b47b0cD257aCf6025c5BFf3b7")
    factoryAddress = Web3.toChecksumAddress("0x0841BD0B734E4F5853f0dD8d7Ea041c241fb0Da6")

    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)

    weth = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
    busd = Web3.toChecksumAddress("0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56")
    base_symbol = "BNB"
    rugdocchain = '&chain=bsc'
    modified = False

elif settings["EXCHANGE"] == 'uniswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://pedantic-montalcini:lair-essay-ranger-rigid-hardy-petted@nd-857-678-344.p2pify.com"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "Uniswap Chain Connected =", client.isConnected())
    print(timestamp(), "Loading Smart Contracts...")
    routerAddress = Web3.toChecksumAddress("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
    factoryAddress = Web3.toChecksumAddress("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    base_symbol = "ETH"
    rugdocchain = '&chain=eth'
    modified = False

elif settings["EXCHANGE"] == 'kuswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://rpc-mainnet.kcc.network"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "Kucoin Chain Connected =", client.isConnected())
    print(timestamp(), "Loading KuSwap Smart Contracts...")
    routerAddress = Web3.toChecksumAddress("0xa58350d6dee8441aa42754346860e3545cc83cda")
    factoryAddress = Web3.toChecksumAddress("0xAE46cBBCDFBa3bE0F02F463Ec5486eBB4e2e65Ae")
    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0x4446Fc4eb47f2f6586f9fAAb68B3498F86C07521")
    base_symbol = "KCS"
    rugdocchain = '&chain=kcc'
    modified = False

elif settings["EXCHANGE"] == 'koffeeswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://rpc-mainnet.kcc.network"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "Kucoin Chain Connected =", client.isConnected())
    print(timestamp(), "Loading KoffeeSwap Smart Contracts...")
    routerAddress = Web3.toChecksumAddress("0xc0fFee0000C824D24E0F280f1e4D21152625742b")
    factoryAddress = Web3.toChecksumAddress("0xC0fFeE00000e1439651C6aD025ea2A71ED7F3Eab")
    routerContract = client.eth.contract(address=routerAddress, abi=koffeeAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0x4446Fc4eb47f2f6586f9fAAb68B3498F86C07521")
    base_symbol = "KCS"
    rugdocchain = '&chain=kcc'
    modified = True

elif settings["EXCHANGE"] == 'spookyswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://rpcapi.fantom.network"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "FANTOM Chain Connected =", client.isConnected())
    print(timestamp(), "Loading Smart Contracts...")
    routerAddress = Web3.toChecksumAddress("0xF491e7B69E4244ad4002BC14e878a34207E38c29")
    factoryAddress = Web3.toChecksumAddress("0x152eE697f2E276fA89E96742e9bB9aB1F2E61bE3")
    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0x21be370d5312f44cb42ce377bc9b8a0cef1a4c83")
    base_symbol = "FTM"
    rugdocchain = '&chain=ftm'
    modified = False

elif settings["EXCHANGE"] == 'spiritswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://rpcapi.fantom.network"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "FANTOM Chain Connected =", client.isConnected())
    print(timestamp(), "Loading Smart Contracts...")
    routerAddress = Web3.toChecksumAddress("0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52")
    factoryAddress = Web3.toChecksumAddress("0xEF45d134b73241eDa7703fa787148D9C9F4950b0")
    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0x21be370d5312f44cb42ce377bc9b8a0cef1a4c83")
    base_symbol = "FTM"
    rugdocchain = '&chain=ftm'
    modified = False

elif settings["EXCHANGE"] == 'quickswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://polygon-rpc.com"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "Matic Chain Connected =", client.isConnected())
    print(timestamp(), "Loading Smart Contracts...")
    routerAddress = Web3.toChecksumAddress("0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff")
    factoryAddress = Web3.toChecksumAddress("0x5757371414417b8c6caad45baef941abc7d3ab32")
    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270")
    base_symbol = "MATIC"
    rugdocchain = '&chain=poly'
    modified = False

elif settings["EXCHANGE"] == 'waultswap':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://rpc-waultfinance-mainnet.maticvigil.com/v1/0bc1bb1691429f1eeee66b2a4b919c279d83d6b0"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "Matic Chain Connected =", client.isConnected())
    print(timestamp(), "Loading Smart Contracts...")
    routerAddress = Web3.toChecksumAddress("0x3a1D87f206D12415f5b0A33E786967680AAb4f6d")
    factoryAddress = Web3.toChecksumAddress("0xa98ea6356A316b44Bf710D5f9b6b4eA0081409Ef")
    routerContract = client.eth.contract(address=routerAddress, abi=routerAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270")
    base_symbol = "MATIC"
    rugdocchain = '&chain=poly'
    modified = False

elif settings["EXCHANGE"] == 'pangolin':
    if settings['USECUSTOMNODE'] == 'true':
        my_provider = settings['CUSTOMNODE']
    else:
        my_provider = "https://api.avax.network/ext/bc/C/rpc"

    client = Web3(Web3.HTTPProvider(my_provider))
    print(timestamp(), "AVAX Chain Connected =", client.isConnected())
    print(timestamp(), "Loading Smart Contracts...")
    routerAddress = Web3.toChecksumAddress("0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106")
    factoryAddress = Web3.toChecksumAddress("0xefa94DE7a4656D787667C749f7E1223D71E9FD88")
    routerContract = client.eth.contract(address=routerAddress, abi=pangolinAbi)
    factoryContract = client.eth.contract(address=factoryAddress, abi=factoryAbi)
    weth = Web3.toChecksumAddress("0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7")
    base_symbol = "AVAX"
    rugdocchain = '&chain=avax'
    modified = True


def get_password():
    # Function: get_password
    # ----------------------------
    # Handles the decision making logic concerning private key encryption and asking the user for their password.
    #
    # returns: the user's password

    settings_changed = False
    setnewpassword = False

    # Check to see if the user has a version of the settings file before private key encryption existed
    if 'ENCRYPTPRIVATEKEYS' not in settings:
        response = ""
        settings_changed = True
        while response != "y" and response != "n":
            print("\nWould you like to use a password to encrypt your private keys?")
            response = input("You will need to input this password each time LimitSwap is executed (y/n): ")

        if response == "y":
            settings['ENCRYPTPRIVATEKEYS'] = "true"
            setnewpassword = True
        else:
            settings['ENCRYPTPRIVATEKEYS'] = "false"

            # If the user wants to encrypt their private keys, but we don't have an encrypted private key recorded, we need to ask for a password
    elif settings['ENCRYPTPRIVATEKEYS'] == "true" and not settings['PRIVATEKEY'].startswith('aes:'):
        print("\nPlease create a password to encrypt your private keys.")
        setnewpassword = True

    # Set a new password when necessary
    if setnewpassword == True:
        settings_changed = True
        passwords_differ = True
        while passwords_differ:
            pwd = pwinput.pwinput(prompt="\nType your new password: ")
            pwd2 = pwinput.pwinput(prompt="\nType your new password again: ")

            if pwd != pwd2:
                print("Error, password mismatch. Try again.")
            else:
                passwords_differ = False

    # The user already has encrypted private keys. Accept a password so we can unencrypt them
    elif settings['ENCRYPTPRIVATEKEYS'] == "true":

        if command_line_args.password:
            pwd = command_line_args.password
        else:
            pwd = pwinput.pwinput(prompt="\nPlease specify the password to decrypt your keys: ")

    else:
        pwd = ""

    if not pwd.strip():
        print()
        print("X WARNING =-= WARNING =-= WARNING =-= WARNING =-= WARNING =-= WARNING=-= WARNING X")
        print("X       You are running LimitSwap without encrypting your private keys.          X")
        print("X     Private keys are stored on disk unencrypted and can be accessed by         X")
        print("X anyone with access to the file system, including the Systems/VPS administrator X")
        print("X       and anyone with physical access to the machine or hard drives.           X")
        print("X WARNING =-= WARNING =-= WARNING =-= WARNING =-= WARNING =-= WARNING=-= WARNING X")
        print()

    if settings_changed == True:
        save_settings(settings, pwd)

    return pwd


# RUGDOC CONTROL IMPLEMENTATION
# Honeypot API details
honeypot_url = 'https://honeypot.api.rugdoc.io/api/honeypotStatus.js?address='

# Rugdoc's answers interpretations
interpretations = {
    "UNKNOWN": (style.RED + '\nThe status of this token is unknown. '
                            'This is usually a system error but could \n also be a bad sign for the token. Be careful.'),
    "OK": (style.GREEN + '\nRUGDOC API RESULT : OK \n'
                         '√ Honeypot tests passed. RugDoc program was able to buy and sell it successfully. This however does not guarantee that it is not a honeypot.'),
    "NO_PAIRS": (style.RED + '\nRUGDOC API RESULT : NO_PAIRS \n'
                             '⚠ Could not find any trading pair for this token on the default router and could thus not test it.'),
    "SEVERE_FEE": (style.RED + '\nRUGDOC API RESULT : SEVERE_FEE \n'
                               '/!\ /!\ A severely high trading fee (over 50%) was detected when selling or buying this token.'),
    "HIGH_FEE": (style.YELLOW + '\nRUGDOC API RESULT : HIGH_FEE \n'
                                '/!\ /!\ A high trading fee (Between 20% and 50%) was detected when selling or buying this token. Our system was however able to sell the token again.'),
    "MEDIUM_FEE": (style.YELLOW + '\nRUGDOC API RESULT : MEDIUM_FEE \n'
                                  '/!\ A trading fee of over 10% but less then 20% was detected when selling or buying this token. Our system was however able to sell the token again.'),
    "APPROVE_FAILED": (style.RED + '\nRUGDOC API RESULT : APPROVE_FAILED \n'
                                   '/!\ /!\ /!\ Failed to approve the token.\n This is very likely a honeypot.'),
    "SWAP_FAILED": (style.RED + '\nRUGDOC API RESULT : SWAP_FAILED \n'
                                '/!\ /!\ /!\ Failed to sell the token. \n This is very likely a honeypot.'),
    "chain not found": (style.RED + '\nRUGDOC API RESULT : chain not found \n'
                                    '/!\ Sorry, rugdoc API does not work on this chain... (it does not work on ETH, mainly) \n')
}


# Function to check rugdoc API
def honeypot_check(address):
    url = (honeypot_url + address + rugdocchain)
    # sending get request and saving the response as response object
    return requests.get(url)


def save_settings(settings, pwd):
    if len(pwd) > 0:
        encrypted_settings = settings.copy()
        encrypted_settings['LIMITWALLETPRIVATEKEY'] = 'aes:' + cryptocode.encrypt(settings['LIMITWALLETPRIVATEKEY'],
                                                                                  pwd)
        encrypted_settings['PRIVATEKEY'] = 'aes:' + cryptocode.encrypt(settings['PRIVATEKEY'], pwd)

    # TODO: MASSAGE OUTPUT - LimitSwap currently loads settings.json as a [0] element, so we need to massage our
    #                  settings.json output so that it's reasable. This should probably be fixed by us importing
    #                  the entire json file, instead of just the [0] element.

    print(timestamp(), "Writing settings to file.")

    if settings['ENCRYPTPRIVATEKEYS'] == "true":
        output_settings = encrypted_settings
    else:
        output_settings = settings

    with open(command_line_args.settings, 'w') as f:
        f.write("[\n")
        f.write(json.dumps(output_settings, indent=4))
        f.write("\n]\n")


def parse_wallet_settings(settings, pwd):
    # Function: load_wallet_settings
    # ----------------------------
    # Handles the process of deciding whether or not the user's private key needs to be decrypted
    # Accepts user input for new private keys and wallet addresses
    #
    # returns: none (exits on incorrect password)

    settings_changed = False

    # Check for limit wallet information
    if " " in settings['LIMITWALLETADDRESS'] or settings['LIMITWALLETADDRESS'] == "":
        settings_changed = True
        settings['LIMITWALLETADDRESS'] = input("Please provide the wallet address where you have your LIMIT: ")

    # Check for limit wallet private key
    if " " in settings['LIMITWALLETPRIVATEKEY'] or settings['LIMITWALLETPRIVATEKEY'] == "":
        settings_changed = True
        settings['LIMITWALLETPRIVATEKEY'] = input(
            "Please provide the private key for the wallet where you have your LIMIT: ")

    # If the limit wallet private key is already set and encrypted, decrypt it
    elif settings['LIMITWALLETPRIVATEKEY'].startswith('aes:'):
        printt("Decrypting limit wallet private key.")
        settings['LIMITWALLETPRIVATEKEY'] = settings['LIMITWALLETPRIVATEKEY'].replace('aes:', "", 1)
        settings['LIMITWALLETPRIVATEKEY'] = cryptocode.decrypt(settings['LIMITWALLETPRIVATEKEY'], pwd)

        if settings['LIMITWALLETPRIVATEKEY'] == False:
            print(style.RED + "ERROR: Your private key decryption password is incorrect")
            print(style.RESET + "Please re-launch the bot and try again")
            sleep(10)
            sys.exit()

    # Check for trading wallet information
    if " " in settings['WALLETADDRESS'] or settings['WALLETADDRESS'] == "":
        settings_changed = True
        settings['WALLETADDRESS'] = input("Please provide the wallet address for your trading wallet: ")

    # Check for trading wallet private key
    if " " in settings['PRIVATEKEY'] or settings['PRIVATEKEY'] == "":
        settings_changed = True
        settings['PRIVATEKEY'] = input("Please provide the private key for the wallet you want to trade with: ")

    # If the trading wallet private key is already set and encrypted, decrypt it
    elif settings['PRIVATEKEY'].startswith('aes:'):
        print(timestamp(), "Decrypting limit wallet private key.")
        settings['PRIVATEKEY'] = settings['PRIVATEKEY'].replace('aes:', "", 1)
        settings['PRIVATEKEY'] = cryptocode.decrypt(settings['PRIVATEKEY'], pwd)

    if settings_changed == True:
        save_settings(settings, pwd)

        
def decimals(address):
    try:
        balanceContract = client.eth.contract(address=Web3.toChecksumAddress(address), abi=standardAbi)
        decimals = balanceContract.functions.decimals().call()
        DECIMALS = 10 ** decimals
    except ABIFunctionNotFound:
        DECIMALS = 10 ** 18
    except ValueError as ve:
        logging.exception(ve)
        print("Please check your SELLPRICE values.")
    return DECIMALS


def check_logs():
    print(timestamp(), "Quickly Checking Log Size")
    with open('./logs/errors.log') as f:
        line_count = 0
        for line in f:
            line_count += 1
        if line_count > 100:
            with open('./logs/errors.log', "r") as f:
                lines = f.readlines()

            with open('./logs/errors.log', "w") as f:
                f.writelines(lines[20:])

    f.close()


def decode_key():
    private_key = settings['LIMITWALLETPRIVATEKEY']
    acct = client.eth.account.privateKeyToAccount(private_key)
    addr = acct.address
    return addr


def check_release():
    try:
        url = 'https://api.github.com/repos/CryptoGnome/LimitSwap/releases/latest'
        r = requests.get(url).json()['tag_name']
        print("Checking Latest Release Version on Github, Please Make Sure You are Staying Updated = ", r)
        logging.info("Checking Latest Release Version on Github, Please Make Sure You are Staying Updated = " + r)
    except Exception:
        r = "github api down, please ignore"

    return r


def auth():
    my_provider2 = 'https://reverent-raman:photo-hamlet-ankle-saved-scared-bobbed@nd-539-402-515.p2pify.com'
    client2 = Web3(Web3.HTTPProvider(my_provider2))
    print(timestamp(), "Connected to Ethereum BlockChain =", client2.isConnected())
    # Insert LIMITSWAP Token Contract Here To Calculate Staked Verification
    address = Web3.toChecksumAddress("0x1712aad2c773ee04bdc9114b32163c058321cd85")
    abi = standardAbi
    balanceContract = client2.eth.contract(address=address, abi=abi)
    decimals = balanceContract.functions.decimals().call()
    DECIMALS = 10 ** decimals

    # Exception for incorrect Key Input
    try:
        decode = decode_key()
    except Exception:
        print("There is a problem with your private key : please check if it's correct. Don't enter seed phrase !")
        logging.info(
            "There is a problem with your private key : please check if it's correct. Don't enter seed phrase !")

    wallet_address = Web3.toChecksumAddress(decode)
    balance = balanceContract.functions.balanceOf(wallet_address).call()
    true_balance = balance / DECIMALS
    print(timestamp(), "Current Tokens Staked =", true_balance)
    logging.info("Current Tokens Staked = " + str(true_balance))
    return true_balance


def approve(address, amount):
    print(timestamp(), "Approval is broken. Skipping", address)
    return 0

    print(timestamp(), "Approving", address)

    eth_balance = Web3.fromWei(client.eth.getBalance(settings['WALLETADDRESS']), 'ether')

    if eth_balance > 0.05:
        print("Estimating Gas Cost Using Web3")
        if settings['EXCHANGE'] == 'uniswap':
            gas = (((client.eth.gasPrice) / 1000000000)) + ((client.eth.gasPrice) / 1000000000) * (int(20) / 100)
            print("Current Gas Price =", gas)

        elif settings['EXCHANGE'] == 'pancakeswap':
            gas = (((client.eth.gasPrice) / 1000000000)) + ((client.eth.gasPrice) / 1000000000) * (int(20) / 100)
            print("Current Gas Price = ", gas)
        elif settings['EXCHANGE'] == 'spiritswap':
            gas = (((client.eth.gasPrice) / 1000000000)) + ((client.eth.gasPrice) / 1000000000) * (int(20) / 100)
            print("Current Gas Price = ", gas)
        elif settings['EXCHANGE'] == 'spookyswap':
            gas = (((client.eth.gasPrice) / 1000000000)) + ((client.eth.gasPrice) / 1000000000) * (int(20) / 100)
            print("Current Gas Price = ", gas)
        elif settings['EXCHANGE'] == 'pangolin':
            gas = (((client.eth.gasPrice) / 1000000000)) + ((client.eth.gasPrice) / 1000000000) * (int(20) / 100)
            print("Current Gas Price = ", gas)
        elif settings['EXCHANGE'] == 'quickswap':
            gas = (((client.eth.gasPrice) / 1000000000)) + ((client.eth.gasPrice) / 1000000000) * (int(20) / 100)
            print("Current Gas Price = ", gas)
        elif settings['EXCHANGE'] == 'kuswap' or 'koffeeswap':
            gas = (((client.eth.gasPrice) / 1000000000)) + ((client.eth.gasPrice) / 1000000000) * (int(20) / 100)
            print("Current Gas Price = ", gas)
        else:
            print("EXCHANGE NAME IN SETTINGS IS SPELLED INCORRECTLY OR NOT SUPPORTED YET CHECK WIKI!")
            logging.info("EXCHANGE NAME IN SETTINGS IS SPELLED INCORRECTLY OR NOT SUPPORTED YET CHECK WIKI!")
            exit()

        contract = client.eth.contract(address=Web3.toChecksumAddress(address), abi=standardAbi)
        transaction = contract.functions.approve(routerAddress, amount).buildTransaction({
            'gasPrice': Web3.toWei(gas, 'gwei'),
            'gas': 300000,
            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
        })
        signed_txn = client.eth.account.signTransaction(transaction, private_key=settings['PRIVATEKEY'])

        try:
            return client.eth.sendRawTransaction(signed_txn.rawTransaction)
        finally:
            print(timestamp(), "Transaction Hash = ", Web3.toHex(client.keccak(signed_txn.rawTransaction)))
            # LOG TX TO JSON
            with open('./transactions.json', 'r') as fp:
                data = json.load(fp)
            tx_hash = client.toHex(client.keccak(signed_txn.rawTransaction))
            tx_input = {"hash": tx_hash}
            data.append(tx_input)
            with open('./transactions.json', 'w') as fp:
                json.dump(data, fp, indent=2)
            fp.close()

            return tx_hash
    else:
        print(timestamp(),
              "You have less than 0.05 ETH/BNB/FTM/MATIC or network gas token in your wallet, bot needs at least 0.05 to cover fees : please add some more in your wallet.")
        logging.info(
            "You have less than 0.05 ETH/BNB/FTM/MATIC or network gas token in your wallet, bot needs at least 0.05 to cover fees : please add some more in your wallet.")
        sleep(10)
        sys.exit()


def check_approval(address, balance):
    print(timestamp(), "Checking Approval Status", address)
    contract = client.eth.contract(address=Web3.toChecksumAddress(address), abi=standardAbi)
    allowance = contract.functions.allowance(Web3.toChecksumAddress(settings['WALLETADDRESS']), routerAddress).call()

    if int(allowance) < int(balance):

        if settings["EXCHANGE"] == 'quickswap':
            print("Revert to Zero To change approval")
            tx = approve(address, 0)
            wait_for_tx(tx, address)
            tx = approve(address, 115792089237316195423570985008687907853269984665640564039457584007913129639935)
            wait_for_tx(tx, address)
        else:
            printt_info("\n                           ---------------------------------------------------------------------------\n"
                        "                           You need to APPROVE this token before selling it : LimitSwap will do it now\n"
                        "                           ---------------------------------------------------------------------------\n")

            tx = approve(address, 115792089237316195423570985008687907853269984665640564039457584007913129639935)
            wait_for_tx(tx, address)
            printt_ok("\n                           ---------------------------------------------------------\n"
                        "                             Token is now approved : LimitSwap can sell this token\n"
                        "                           ---------------------------------------------------------\n")

        return

    else:
        pass


def check_bnb_balance():
    balance = client.eth.getBalance(settings['WALLETADDRESS'])
    print(timestamp(), "Current Wallet Balance is :", Web3.fromWei(balance, 'ether'), base_symbol)
    return balance


def check_balance(address, symbol='UNKNOWN_TOKEN', max_wait_time=30, more_tokens_than=0):
    # Function: check_balance
    # --------------------
    # check user's wallet for the balance of tokens belonging to address
    #
    # address - the contract address of the token we're looking for
    # symbol  - the symbol of the token we're looking for
    # max_wait_time - the maximum amount of time in seconds to wait for a balance to show
    # more_tokens_than - if the wallet has more tokens than this, than it's considered to have accepted tokens
    #
    # returns: 0 - txn_receipt['status'] on unknown
    #          1 - txn_receipt['status'] on success (sometimes reverted)
    #          2 - failed with an empty log (rejected by contract)
    #         -1 -  transaction failed due to unknown reason

    balance = 0

    address = Web3.toChecksumAddress(address)
    DECIMALS = decimals(address)
    balanceContract = client.eth.contract(address=address, abi=standardAbi)
    
    if max_wait_time == 0:
        balance = balanceContract.functions.balanceOf(settings['WALLETADDRESS']).call()
    elif max_wait_time > 0:
        exit_timestamp = time() + max_wait_time

        while exit_timestamp > time() and balance <= more_tokens_than:
            balance = balanceContract.functions.balanceOf(settings['WALLETADDRESS']).call()
            sleep(50/1000)

    print(timestamp(), "Current Wallet Balance is: " + str(balance / DECIMALS) + " " + symbol)

    return balance


def fetch_pair(inToken, outToken):
    print(timestamp(), "Fetching Pair Address")
    pair = factoryContract.functions.getPair(inToken, outToken).call()
    print(timestamp(), "Pair Address = ", pair)
    return pair


def sync(inToken, outToken):
    pair = factoryContract.functions.getPair(inToken, outToken).call()
    syncContract = client.eth.contract(address=Web3.toChecksumAddress(pair), abi=lpAbi)
    sync = syncContract.functions.sync().call()


def check_pool(inToken, outToken, symbol):
    # This function is made to calculate Liquidity of a token
    pair_address = factoryContract.functions.getPair(inToken, outToken).call()
    DECIMALS = decimals(outToken)
    pair_contract = client.eth.contract(address=pair_address, abi=lpAbi)
    reserves = pair_contract.functions.getReserves().call()

    # Tokens are ordered by the token contract address
    # The token contract address can be interpreted as a number
    # And the smallest one will be token0 internally

    ctnb1 = int(inToken, 16)
    ctnb2 = int(outToken, 16)

    if (ctnb1 > ctnb2):
        printt_debug ("reserves[0] is for outToken:")
        pooled = reserves[0] / DECIMALS
    else:
        printt_debug ("reserves[0] is for inToken:")
        pooled = reserves[1] / DECIMALS


    printt_debug ("----------------------------------------------------------------------")
    printt_debug ("Debug reserves[0] line 982:     ", reserves[0] / DECIMALS)
    printt_debug ("Debug reserves[1] line 982:     ", reserves[1] / DECIMALS)
    printt_debug ("----------------------------------------------------------------------")
    printt_debug ("Debug LIQUIDITYAMOUNT line 981 :", pooled, "in token:", outToken)
    printt_debug ("----------------------------------------------------------------------")

    return pooled


def get_tokens_purchased(tx_hash):
    # Function: get_tokens_purchased
    # ----------------------------
    # provides the number of tokens purchased in a transaction
    #
    # tx_hash = the transaction hash
    #
    # returns: number of tokens purchased

    # Get transaction object
    tx = client.eth.get_transaction(tx_hash)
    contract = client.eth.contract(address=tx["to"], abi=lpAbi)

    # decode input data using contract object's decode_function_input() method
    func_obj, func_params = contract.decode_function_input(tx["input"])
    print (func_params)
    exit(0)
 

def check_price(inToken, outToken, symbol, base, custom, routing, buypriceinbase, sellpriceinbase, stoplosspriceinbase):
    # CHECK GET RATE OF THE TOKEn

    DECIMALS = decimals(inToken)
    stamp = timestamp()

    if custom == 'false':
        base = base_symbol
    else:
        pass

    if routing == 'true':
        if outToken != weth:
            price_check = routerContract.functions.getAmountsOut(1 * DECIMALS, [inToken, weth, outToken]).call()[-1]
            DECIMALS = decimals(outToken)
            tokenPrice = price_check / DECIMALS
            print(stamp, symbol, " Price ", tokenPrice, base, "//// your buyprice =", buypriceinbase, base,
                  "//// your sellprice =", sellpriceinbase, base, "//// your stoplossprice =", stoplosspriceinbase, base)
        else:
            price_check = routerContract.functions.getAmountsOut(1 * DECIMALS, [inToken, weth]).call()[-1]
            DECIMALS = decimals(outToken)
            tokenPrice = price_check / DECIMALS
            price_output = "{:.18f}".format(tokenPrice)
            print(stamp, symbol, "Price =", price_output, base, "//// your buyprice =", buypriceinbase, base,
                  "//// your sellprice =", sellpriceinbase, base, "//// your stoplossprice =", stoplosspriceinbase, base)

    else:
        if outToken != weth:
            price_check = routerContract.functions.getAmountsOut(1 * DECIMALS, [inToken, outToken]).call()[-1]
            DECIMALS = decimals(outToken)
            tokenPrice = price_check / DECIMALS
            print(stamp, symbol, " Price ", tokenPrice, base, "//// your buyprice =", buypriceinbase, base,
                  "//// your sellprice =", sellpriceinbase, base, "//// your stoplossprice =", stoplosspriceinbase, base)
        else:
            price_check = routerContract.functions.getAmountsOut(1 * DECIMALS, [inToken, weth]).call()[-1]
            DECIMALS = decimals(outToken)
            tokenPrice = price_check / DECIMALS
            price_output = "{:.18f}".format(tokenPrice)
            print(stamp, symbol, "Price =", price_output, base, "//// your buyprice =", buypriceinbase, base,
                  "//// your sellprice =", sellpriceinbase, base, "//// your stoplossprice =", stoplosspriceinbase, base)

    return tokenPrice


def wait_for_tx(tx_hash, address, max_wait_time=60):
    # Function: wait_for_tx
    # --------------------
    # waits for a transaction to complete.
    #
    # tx_hash - the transaction hash
    # address - the wallet address sending the transaction
    # max_wait_time - the maximum amoun of time in seconds to wait for a transaction to complete
    #
    # global failedtransactionsamount - the number of times a transaction has failed
    #
    # returns: 0 - txn_receipt['status'] on unknown
    #          1 - txn_receipt['status'] on success (sometimes reverted)
    #          2 - failed with an empty log (rejected by contract)
    #         -1 -  transaction failed due to unknown reason

    global failedtransactionsamount
   
    if max_wait_time > 0:
        exit_timestamp = time() + max_wait_time

    loop_iterations = 0
    got_receipt = False

    while got_receipt == False and exit_timestamp > time():
        
        if loop_iterations == 0:
            print (timestamp(), style.INFO, " Checking for transaction confirmation", style.RESET, sep='',  end='', flush=True)
        elif loop_iterations == 1:
            print (style.INFO, " (waiting ", max_wait_time, " seconds)", style.RESET, sep='', end="", flush=True)
        else:
            print (style.INFO, ".", style.RESET, sep='', end="", flush=True)
            sleep(1)
        loop_iterations = loop_iterations + 1
        
        try:
            txn_receipt = client.eth.wait_for_transaction_receipt(tx_hash,1)
            got_receipt = True
        except Exception as e:
            txn_receipt = None

    print('')
    if got_receipt == True and len(txn_receipt['logs']) != 0:
        return_value = txn_receipt['status']
        printt_ok("Transaction was successful with a status code of", return_value)
    
    elif got_receipt == True and len(txn_receipt['logs']) == 0:
        failedtransactionsamount += 1
        return_value = 2
        printt_err("Transaction was rejected by contract with a status code of", txn_receipt['status'])
    
    elif txn_receipt is not None and txn_receipt['blockHash'] is not None:
        return_value = txn_receipt['status']
        printt_warn("Transaction receipt returned with an unknown status and a status code of", return_value)
    
    else:
        # We definitely get this far if the node is down
        print("\n")
        printt_err("Transaction was not confirmed after", max_wait_time, "seconds: something wrong happened.\n"
                    "                           Please check if :\n"
                    "                           - your node is running correctly\n"
                    "                           - you have enough Gaslimit (check 'Gas Used by Transaction') if you have a failed Tx\n")
        failedtransactionsamount += 1
        return_value = -1

    return return_value

def preapprove(tokens):
    for token in tokens:
        check_approval(token['ADDRESS'], 115792089237316195423570985008687907853269984665640564039457584007913129639935)

        if token['USECUSTOMBASEPAIR'] == 'false':
            check_approval(weth, 115792089237316195423570985008687907853269984665640564039457584007913129639935)
        else:
            check_approval(token['BASEADDRESS'],
                           115792089237316195423570985008687907853269984665640564039457584007913129639935)


def buy(amount, inToken, outToken, gas, slippage, gaslimit, boost, fees, custom, symbol, base, routing, waitseconds,
        failedtransactionsnumber):
        
    seconds = int(waitseconds)
    if int(failedtransactionsamount) == int(failedtransactionsnumber):
        printt_err("\n                           ---------------------------------------------------------------\n"
                        "                             Bot has reached maximum FAILED TRANSACTIONS number: it stops\n"
                        "                           ---------------------------------------------------------------\n\n")

        logging.info("Bot has reached maximum FAILED TRANSACTIONS number: it stops")
        sleep(10)
        sys.exit()
    else:

        if waitseconds != '0':
            printt_info("Bot will wait", waitseconds, " seconds before buy, as you entered in BUYAFTER_XXX_SECONDS parameter")
            sleep(seconds)

        print(timestamp(), "Placing New Buy Order for " + symbol)

        if int(gaslimit) < 250000:
            printt_info("Your GASLIMIT parameter is too low : LimitSwap has forced it to 300000 otherwise your transaction would fail for sure. We advise you to raise it to 1000000.")
            gaslimit = 300000

        if custom == 'false':
            balance = Web3.fromWei(check_bnb_balance(), 'ether')
            base = base_symbol
        else:
            address = Web3.toChecksumAddress(inToken)
            DECIMALS = decimals(address)
            balance_check = check_balance(inToken, base)
            balance = balance_check / DECIMALS

        if balance > Decimal(amount):
            if gas == 'boost':
                gas_check = client.eth.gasPrice
                gas_price = gas_check / 1000000000
                gas = (gas_price * ((int(boost)) / 100)) + gas_price
            else:
                gas = int(gas)

            gaslimit = int(gaslimit)
            slippage = int(slippage)
            DECIMALS = decimals(inToken)
            amount = int(float(amount) * DECIMALS)

            if custom == 'false':
                # if USECUSTOMBASEPAIR = false

                if routing == 'false':
                    # LIQUIDITYINNATIVETOKEN = false
                    # USECUSTOMBASEPAIR = false
                    printt_err("You have selected LIQUIDITYINNATIVETOKEN = false , so you must choose USECUSTOMBASEPAIR = true \n"
                               "Please read Wiki carefully, it's very important you can lose money!!")
                    sleep(10)
                    sys.exit()
                else:
                    amount_out = routerContract.functions.getAmountsOut(amount, [weth, outToken]).call()[-1]
                    if settings['UNLIMITEDSLIPPAGE'] == 'true':
                        min_tokens = 100
                    else:
                        min_tokens = int(amount_out * (1 - (slippage / 100)))

                    deadline = int(time() + + 60)

                    # THIS SECTION IS FOR MODIFIED CONTRACTS : EACH EXCHANGE NEEDS TO BE SPECIFIED
                    # USECUSTOMBASEPAIR = false
                    if modified == True:

                        if settings["EXCHANGE"] == 'koffeeswap':
                            transaction = routerContract.functions.swapExactKCSForTokens(
                                min_tokens,
                                [weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'value': amount,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

                        elif settings["EXCHANGE"] == 'pangolin' or settings["EXCHANGE"] == 'traderjoe':
                            transaction = routerContract.functions.swapExactAVAXForTokens(
                                min_tokens,
                                [weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'value': amount,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })


                    else:
                        # USECUSTOMBASEPAIR = false
                        # This section is for exchange with Modified = false --> uniswap / pancakeswap / apeswap, etc.

                        # Special condition on Uniswap, to implement EIP-1559
                        if settings["EXCHANGE"] == 'uniswap':
                            transaction = routerContract.functions.swapExactETHForTokens(
                                min_tokens,
                                [weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                                'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                                'type': "0x02"
                            })

                        else:
                            # USECUSTOMBASEPAIR = false
                            # for all the rest of exchanges with Modified = false
                            transaction = routerContract.functions.swapExactETHForTokens(
                                min_tokens,
                                [weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'value': amount,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

            else:
                # USECUSTOMBASEPAIR = true
                if inToken == weth:
                    # USECUSTOMBASEPAIR = true
                    # but user chose to put WETH or WBNB contract as CUSTOMBASEPAIR address
                    amount_out = routerContract.functions.getAmountsOut(amount, [weth, outToken]).call()[-1]
                    if settings['UNLIMITEDSLIPPAGE'] == 'true':
                        min_tokens = 100
                    else:
                        min_tokens = int(amount_out * (1 - (slippage / 100)))
                    deadline = int(time() + + 60)

                    if settings["EXCHANGE"] == 'uniswap':
                        # Special condition on Uniswap, to implement EIP-1559
                        transaction = routerContract.functions.swapExactTokensForTokens(
                            amount,
                            min_tokens,
                            [weth, outToken],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                            'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                            'type': "0x02"
                        })

                    else:
                        transaction = routerContract.functions.swapExactTokensForTokens(
                            amount,
                            min_tokens,
                            [weth, outToken],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'gasPrice': Web3.toWei(gas, 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                        })

                else:
                    # LIQUIDITYINNATIVETOKEN = true
                    # USECUSTOMBASEPAIR = true
                    # Base Pair different from weth
                    if routing == 'true':
                        amount_out = routerContract.functions.getAmountsOut(amount, [inToken, weth, outToken]).call()[
                            -1]
                        if settings['UNLIMITEDSLIPPAGE'] == 'true':
                            min_tokens = 100
                        else:
                            min_tokens = int(amount_out * (1 - (slippage / 100)))
                        deadline = int(time() + + 60)

                        if settings["EXCHANGE"] == 'uniswap':
                            # USECUSTOMBASEPAIR = true
                            # Base Pair different from weth
                            # LIQUIDITYINNATIVETOKEN = true

                            # Special condition on Uniswap, to implement EIP-1559
                            transaction = routerContract.functions.swapExactTokensForTokens(
                                amount,
                                min_tokens,
                                [inToken, weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                                'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                                'type': "0x02"
                            })

                        else:
                            # USECUSTOMBASEPAIR = true
                            # Base Pair different from weth
                            # LIQUIDITYINNATIVETOKEN = true
                            # Exchange different from Uniswap

                            transaction = routerContract.functions.swapExactTokensForTokens(
                                amount,
                                min_tokens,
                                [inToken, weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

                    else:
                        # LIQUIDITYINNATIVETOKEN = false
                        # USECUSTOMBASEPAIR = true
                        # Base Pair different from weth

                        amount_out = routerContract.functions.getAmountsOut(amount, [inToken, outToken]).call()[-1]
                        if settings['UNLIMITEDSLIPPAGE'] == 'true':
                            min_tokens = 100
                        else:
                            min_tokens = int(amount_out * (1 - (slippage / 100)))
                        deadline = int(time() + + 60)

                        if settings["EXCHANGE"] == 'uniswap':
                            # LIQUIDITYINNATIVETOKEN = false
                            # USECUSTOMBASEPAIR = true
                            # Base Pair different from weth
                            # Special condition on Uniswap, to implement EIP-1559

                            transaction = routerContract.functions.swapExactTokensForTokens(
                                amount,
                                min_tokens,
                                [inToken, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                                'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                                'type': "0x02"
                            })

                        else:
                            # LIQUIDITYINNATIVETOKEN = false
                            # USECUSTOMBASEPAIR = true
                            # Base Pair different from weth
                            # Exchange different from Uniswap

                            transaction = routerContract.functions.swapExactTokensForTokens(
                                amount,
                                min_tokens,
                                [inToken, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

            sync(inToken, outToken)
            signed_txn = client.eth.account.signTransaction(transaction, private_key=settings['PRIVATEKEY'])

            try:
                return client.eth.sendRawTransaction(signed_txn.rawTransaction)
            finally:
                print(timestamp(), "Transaction Hash = ", Web3.toHex(client.keccak(signed_txn.rawTransaction)))
                # LOG TX TO JSON
                with open('./transactions.json', 'r') as fp:
                    data = json.load(fp)
                tx_hash = client.toHex(client.keccak(signed_txn.rawTransaction))
                tx_input = {"hash": tx_hash}
                data.append(tx_input)
                with open('./transactions.json', 'w') as fp:
                    json.dump(data, fp, indent=2)
                fp.close()

                return tx_hash

        else:
            printt_err("Not Enough " + base + " Balance to make buys")
            logging.info("Not Enough " + base + " Balance to make buys")
            sleep(5)
            return False


def sell(amount, moonbag, inToken, outToken, gas, slippage, gaslimit, boost, fees, custom, symbol, routing):
    print(timestamp(), "Placing Sell Order " + symbol)
    balance = Web3.fromWei(check_balance(inToken, symbol), 'ether')
    check_approval(inToken, balance * 1000000000)

    if int(gaslimit) < 250000:
        gaslimit = 300000

    if type(amount) == str:
        amount_check = balance
    else:
        amount_check = Decimal(amount)

    if balance >= Decimal(amount_check) and balance > 0.0000000000000001:

        if gas == 'boost':
            gas_check = client.eth.gasPrice
            gas_price = gas_check / 1000000000
            gas = (gas_price * ((int(boost) * 4) / 100)) + gas_price
        else:
            gas = int(gas)

        slippage = int(slippage)
        gaslimit = int(gaslimit)
        DECIMALS = decimals(inToken)

        if amount.lower() == 'all':
            balance = check_balance(inToken, symbol)
            moonbag = int(Decimal(moonbag) * DECIMALS)
            amount = int(Decimal(balance - moonbag))

        else:
            balance = check_balance(inToken, symbol)
            amount = Decimal(amount) * DECIMALS
            moonbag = int(Decimal(moonbag) * DECIMALS)

            if balance < amount:
                print(timestamp(), "Selling Remaining ", symbol)
                amount = int(Decimal(balance - moonbag))
            else:
                amount = int(Decimal(balance - moonbag))
                if amount > 0:
                    print(timestamp(), "Selling", amount / DECIMALS, symbol)
                else:
                    print("Not enough left to sell, would bust moonbag")
                    amount = 0

        if custom == 'false':
            # USECUSTOMBASEPAIR = false
            sync(inToken, weth)

            amount_out = routerContract.functions.getAmountsOut(amount, [inToken, weth]).call()[-1]
            min_tokens = int(amount_out * (1 - (slippage / 100)))
            deadline = int(time() + + 60)

            if fees == 'true':

                # THIS SECTION IS FOR MODIFIED CONTRACTS AND EACH EXCHANGE IS SPECIFIED
                if modified == True:
                    # USECUSTOMBASEPAIR = false
                    # HASFEES = true

                    if settings["EXCHANGE"] == 'koffeeswap':
                        transaction = routerContract.functions.swapExactTokensForKCSSupportingFeeOnTransferTokens(
                            amount,
                            min_tokens,
                            [inToken, weth],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'gasPrice': Web3.toWei(gas, 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                        })

                    if settings["EXCHANGE"] == 'pangolin' or settings["EXCHANGE"] == 'traderjoe':
                        transaction = routerContract.functions.swapExactTokensForAVAXSupportingFeeOnTransferTokens(
                            amount,
                            min_tokens,
                            [inToken, weth],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'gasPrice': Web3.toWei(gas, 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                        })

                else:
                    # This section is for exchange with Modified = false --> uniswap / pancakeswap / apeswap, etc.
                    # USECUSTOMBASEPAIR = false
                    # HASFEES = true
                    transaction = routerContract.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
                        amount,
                        min_tokens,
                        [inToken, weth],
                        Web3.toChecksumAddress(settings['WALLETADDRESS']),
                        deadline
                    ).buildTransaction({
                        'gasPrice': Web3.toWei(gas, 'gwei'),
                        'gas': gaslimit,
                        'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                        'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                    })
            else:
                # USECUSTOMBASEPAIR = false
                # HASFEES = false

                # THIS SECTION IS FOR MODIFIED CONTRACTS AND EACH EXCHANGE IS SPECIFIED
                if modified == True:
                    # USECUSTOMBASEPAIR = false
                    # HASFEES = false
                    # Modified = true

                    if settings["EXCHANGE"] == 'koffeeswap':
                        transaction = routerContract.functions.swapExactTokensForKCS(
                            amount,
                            min_tokens,
                            [inToken, outToken],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'gasPrice': Web3.toWei(gas, 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                        })
                    elif settings["EXCHANGE"] == 'pangolin' or settings["EXCHANGE"] == 'traderjoe':
                        transaction = routerContract.functions.swapExactTokensForAVAX(
                            amount,
                            min_tokens,
                            [inToken, outToken],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'gasPrice': Web3.toWei(gas, 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                        })

                else:
                    # USECUSTOMBASEPAIR = false
                    # HASFEES = false
                    # Modified = false --> uniswap / pancakeswap / apeswap, etc.

                    if settings["EXCHANGE"] == 'uniswap':
                        # Special condition on Uniswap, to implement EIP-1559
                        transaction = routerContract.functions.swapExactTokensForETH(
                            amount,
                            min_tokens,
                            [inToken, outToken],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                            'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                            'type': "0x02"
                        })

                    else:
                        # for all the rest of exchanges with Modified = false
                        transaction = routerContract.functions.swapExactTokensForETH(
                            amount,
                            min_tokens,
                            [inToken, outToken],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'gasPrice': Web3.toWei(gas, 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                        })

        else:
            # USECUSTOMBASEPAIR = true
            if outToken == weth:
                # if user has set WETH or WBNB as Custom base pair
                sync(inToken, outToken)
                amount_out = routerContract.functions.getAmountsOut(amount, [inToken, weth]).call()[-1]
                min_tokens = int(amount_out * (1 - (slippage / 100)))
                deadline = int(time() + + 60)

                if fees == 'true':
                    # USECUSTOMBASEPAIR = true
                    # HASFEES = true

                    if int(gaslimit) < 950000:
                        gaslimit = 950000

                    # THIS SECTION IS FOR MODIFIED CONTRACTS AND EACH EXCHANGE IS SPECIFIED
                    if modified == True:
                        # USECUSTOMBASEPAIR = true
                        # HASFEES = true
                        # Modified = true

                        if settings["EXCHANGE"] == 'koffeeswap':
                            transaction = routerContract.functions.swapExactTokensForKCSSupportingFeeOnTransferTokens(
                                amount,
                                min_tokens,
                                [inToken, weth],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

                        elif settings["EXCHANGE"] == 'pangolin' or settings["EXCHANGE"] == 'traderjoe':
                            transaction = routerContract.functions.swapExactTokensForAVAXSupportingFeeOnTransferTokens(
                                amount,
                                min_tokens,
                                [inToken, weth],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

                    else:
                        # USECUSTOMBASEPAIR = true
                        # HASFEES = true
                        # Modified = false

                        transaction = routerContract.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
                            amount,
                            min_tokens,
                            [inToken, weth],
                            Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            deadline
                        ).buildTransaction({
                            'gasPrice': Web3.toWei(gas, 'gwei'),
                            'gas': gaslimit,
                            'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                            'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                        })
                else:
                    # USECUSTOMBASEPAIR = true
                    # HASFEES = false
                    transaction = routerContract.functions.swapExactTokensForTokens(
                        amount,
                        min_tokens,
                        [inToken, weth],
                        Web3.toChecksumAddress(settings['WALLETADDRESS']),
                        deadline
                    ).buildTransaction({
                        'gasPrice': Web3.toWei(gas, 'gwei'),
                        'gas': gaslimit,
                        'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                        'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                    })


            else:
                sync(inToken, outToken)

                if routing == 'false' and outToken != weth:
                    # LIQUIDITYINNATIVETOKEN = false
                    # USECUSTOMBASEPAIR = true
                    amount_out = routerContract.functions.getAmountsOut(amount, [inToken, outToken]).call()[-1]
                    min_tokens = int(amount_out * (1 - (slippage / 100)))
                    deadline = int(time() + + 60)

                    if fees == 'true':
                        # LIQUIDITYINNATIVETOKEN = false
                        # USECUSTOMBASEPAIR = true
                        # HASFEES = true
                        if settings["EXCHANGE"] == 'uniswap':
                            # Special condition on Uniswap, to implement EIP-1559
                            transaction = routerContract.functions.swapExactTokensForTokensSupportingFeeOnTransferTokens(
                                amount,
                                min_tokens,
                                [inToken, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                                'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                                'type': "0x02"
                            })

                        else:
                            # for all the rest of exchanges
                            transaction = routerContract.functions.swapExactTokensForTokensSupportingFeeOnTransferTokens(
                                amount,
                                min_tokens,
                                [inToken, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

                    else:
                        # LIQUIDITYINNATIVETOKEN = false
                        # USECUSTOMBASEPAIR = true
                        # HASFEES = false
                        if settings["EXCHANGE"] == 'uniswap':
                            # Special condition on Uniswap, to implement EIP-1559
                            transaction = routerContract.functions.swapExactTokensForTokens(
                                amount,
                                min_tokens,
                                [inToken, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                                'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                                'type': "0x02"
                            })

                        else:
                            # for all the rest of exchanges
                            transaction = routerContract.functions.swapExactTokensForTokens(
                                amount,
                                min_tokens,
                                [inToken, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

                elif routing == 'false' and outToken == weth:
                    # LIQUIDITYINNATIVETOKEN = false
                    # USECUSTOMBASEPAIR = true
                    # but user chose to put WETH or WBNB contract as CUSTOMBASEPAIR address
                    printt_err(
                        "ERROR IN YOUR TOKENS.JSON : YOU NEED TO CHOOSE THE PROPER BASE PAIR AS SYMBOL IF YOU ARE TRADING OUTSIDE OF NATIVE LIQUIDITY POOL")

                else:
                    amount_out = routerContract.functions.getAmountsOut(amount, [inToken, weth, outToken]).call()[-1]
                    min_tokens = int(amount_out * (1 - (slippage / 100)))
                    deadline = int(time() + + 60)

                    if fees == 'true':
                        # HASFEES = true
                        if settings["EXCHANGE"] == 'uniswap':
                            # Special condition on Uniswap, to implement EIP-1559
                            transaction = routerContract.functions.swapExactTokensForTokensSupportingFeeOnTransferTokens(
                                amount,
                                min_tokens,
                                [inToken, weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                                'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                                'type': "0x02"
                            })

                        else:
                            transaction = routerContract.functions.swapExactTokensForTokensSupportingFeeOnTransferTokens(
                                amount,
                                min_tokens,
                                [inToken, weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

                    else:
                        # HASFEES = false
                        if settings["EXCHANGE"] == 'uniswap':
                            # Special condition on Uniswap, to implement EIP-1559
                            transaction = routerContract.functions.swapExactTokensForTokens(
                                amount,
                                min_tokens,
                                [inToken, weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'maxFeePerGas': Web3.toWei(gas, 'gwei'),
                                'maxPriorityFeePerGas': Web3.toWei('1.5', 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS']),
                                'type': "0x02"
                            })
                        else:
                            transaction = routerContract.functions.swapExactTokensForTokens(
                                amount,
                                min_tokens,
                                [inToken, weth, outToken],
                                Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                deadline
                            ).buildTransaction({
                                'gasPrice': Web3.toWei(gas, 'gwei'),
                                'gas': gaslimit,
                                'from': Web3.toChecksumAddress(settings['WALLETADDRESS']),
                                'nonce': client.eth.getTransactionCount(settings['WALLETADDRESS'])
                            })

        sync(inToken, outToken)
        signed_txn = client.eth.account.signTransaction(transaction, private_key=settings['PRIVATEKEY'])

        try:
            return client.eth.sendRawTransaction(signed_txn.rawTransaction)
        finally:
            print(timestamp(), "Transaction Hash = ", Web3.toHex(client.keccak(signed_txn.rawTransaction)))
            # LOG TX TO JSON
            with open('./transactions.json', 'r') as fp:
                data = json.load(fp)
            tx_hash = client.toHex(client.keccak(signed_txn.rawTransaction))
            tx_input = {"hash": tx_hash}
            data.append(tx_input)
            with open('./transactions.json', 'w') as fp:
                json.dump(data, fp, indent=2)
            fp.close()

            return tx_hash
    else:
        pass


def run():
    global failedtransactionsamount

    try:
        
        tokens = load_tokens_file(command_line_args.tokens, True)

        eth_balance = Web3.fromWei(client.eth.getBalance(settings['WALLETADDRESS']), 'ether')

        if eth_balance < 0.05:
            printt_err("You have less than 0.05 ETH/BNB/FTM/MATIC/Etc. token in your wallet, bot needs at least 0.05 to cover fees : please add some more in your wallet")
            sleep(10)
            exit(1)

        # Display the number of token pairs we're attempting to trade
        # TODO: I have plans to prune failed tokens and duplicate pairs, so displaying this information is going to become important
        printt("Quantity of tokens attempting to trade:", len(tokens), "(" , build_token_list(tokens) , ")")


        # Check to see if the user wants to pre-approve token transactions. If they do, work through that approval process
        if settings['PREAPPROVE'] == 'true':
            preapprove(tokens)

        # For each token check to see if the user wants to run a rugdoc check against them.
        #   then run the rugdoctor check and prompt the user if they want to continue trading
        #   the token
        #
        # TODO PRUNE: Prune tokens if the user doesn't want to trade them. Exit only if we don't have any more tokens left
        # TODO ARG: Implement an argument that auto accepts or prunes tokens that are rejected/accepted by the rugdoc check
        for token in tokens:
            
            if token['RUGDOC_CHECK'] == 'true':

                honeypot = honeypot_check(address=token['ADDRESS'])
                d = json.loads(honeypot.content)
                for key, value in interpretations.items():
                    if d["status"] in key:
                        honeypot_status = value
                        honeypot_code = key
                        print(honeypot_status)

                decision = ""
                while decision != "y" and decision != "n":
                    print ("\nWhat is your decision?")
                    decision = input("Would you like to snipe this token? (y/n): ")

                if decision == "y":
                    print ("\nOK let's go!!\n")
                else:
                    sys.exit()
        
        load_token_file_increment = 0

        while True:

            # Load the tokens file, approximately every 5 seconds, which even on the worst nodes is about
            #   once a second
            if load_token_file_increment > 5:
                tokens = load_tokens_file(command_line_args.tokens, False)
                load_token_file_increment = 0
            else:
                load_token_file_increment = load_token_file_increment + 1

            for token in tokens:
                
                if token['ENABLED'] == 'true':

                    # Set the checksum addressed for the addresses we're working with
                    # TODO: We should do this once and store the values
                    inToken = Web3.toChecksumAddress(token['ADDRESS'])

                    if token['USECUSTOMBASEPAIR'] == 'true':
                        outToken = Web3.toChecksumAddress(token['BASEADDRESS'])
                    else:
                        outToken = weth


                    #
                    #  CHECK FOR LIQUIDITY OR PRICE CHECK
                    #    Check the latest price, which will also tell us if we have liquidity
                    #                    
                    try:
                        quote = check_price(inToken, outToken, token['SYMBOL'], token['BASESYMBOL'],
                                            token['USECUSTOMBASEPAIR'], token['LIQUIDITYINNATIVETOKEN'],
                                            token['BUYPRICEINBASE'], token['SELLPRICEINBASE'], token['STOPLOSSPRICEINBASE'])
                        pool = check_pool(inToken, outToken, token['BASESYMBOL'])
                        
                        printt_debug ("Liquidity Reserves:", float(pool))
                        printt_debug ("inToken :", inToken, " outToken :", outToken)

                    except Exception:
                        printt(token['SYMBOL'],"Not Listed For Trade Yet... waiting for liquidity to be added on exchange")
                        quote = 0
                    
                    printt_debug ("Liquidity check complete")
                    printt_debug ("Quote :", quote)
                    printt_debug ("BuyPrice", Decimal(token['BUYPRICEINBASE']))
                    printt_debug ("Reached MAX TOKENS", token['_REACHED_MAX_TOKENS'])

                    # If quote is not equal to zero, I'm going to be needing my balance for buy and sell decisions
                    #   and I'm going to need to know if I've reached my MAXTOKENS
                    if quote !=0:
                        balance = check_balance(inToken, token['SYMBOL'], 0)
                        DECIMALS = decimals(inToken)
                        if Decimal(balance / DECIMALS) < Decimal(token['MAXTOKENS']):
                            token['_REACHED_MAX_TOKENS'] = True
                            printt_info ("You have reached the maximum number of tokens for this position.")
                    #
                    # BUY CHECK
                    #   If the liquidity check has returned a quote that is less than our BUYPRICEINBASE and we haven't informrmed
                    #   the user that we've reached the maximum number of tokens, check for other criteria to buy.
                    #
                    if quote != 0 and quote < Decimal(token['BUYPRICEINBASE']) and token['_REACHED_MAX_TOKENS'] == False:

                        printt_debug("Checking sell conditions")
                        
                        #
                        #  CHECK FOR LIQUIDITY AMOUNT
                        #    If we've found liquidity and want to check for liquidity amount, do that here
                        #
                        if token["LIQUIDITYCHECK"] == 'true' and token['_LIQUIDITY_CHECKED'] == False:
                            pool = check_pool(inToken, outToken, token['BASESYMBOL'])
                            printt("You have set LIQUIDITYCHECK = true.")
                            printt("Current", token['SYMBOL'], "Liquidity =", int(pool), "in token:",outToken)

                            if float(token['LIQUIDITYAMOUNT']) <= float(pool):
                                printt_ok("LIQUIDITYAMOUNT parameter =", int(token['LIQUIDITYAMOUNT']),
                                            " --> Enough liquidity detected : Buy Signal Found!")
                            
                            # This position isn't looking good. Inform the user, disable the token and break out of this loop
                            else:
                                printt_warn("LIQUIDITYAMOUNT parameter =", int(token['LIQUIDITYAMOUNT']),
                                        " : not enough liquidity, bot will not buy. Disableing the trade of this token.")
                                token['ENABLED'] = 'false'
                                quote = 0
                                break

                        #
                        # PURCHASE POSITION
                        #   If we've passed all checks, attempt to purchase the token

                        log_price = "{:.18f}".format(quote)
                        logging.info("Buy Signal Found @" + str(log_price))
                        printt("Buy Signal Found!")

                        if command_line_args.sim_buy:
                            tx = command_line_args.sim_buy
                        else:
                            tx = buy(token['BUYAMOUNTINBASE'], outToken, inToken, token['GAS'],
                                        token['SLIPPAGE'], token['GASLIMIT'], token['BOOSTPERCENT'],
                                        token["HASFEES"], token['USECUSTOMBASEPAIR'], token['SYMBOL'],
                                        token['BASESYMBOL'], token['LIQUIDITYINNATIVETOKEN'],
                                        token['BUYAFTER_XXX_SECONDS'], token['MAX_FAILED_TRANSACTIONS_IN_A_ROW'])

                        if tx != False:
                            tx = wait_for_tx(tx, token['ADDRESS'])
                            balance = check_balance(token['ADDRESS'], token['BALANCE'])
                            print(
                                style.RESET + "\n                           --------------------------------------\n"
                                                "                            √  Tx done. Check your wallet \n"
                                                "                           --------------------------------------")
                            print(style.RESET + "")
                            sleep(3)
                            check_balance(token['ADDRESS'], token['SYMBOL'])
                            print(style.RESET + "\n")
                            sleep(3)

                            if tx != 1:
                                # transaction is a FAILURE
                                print(
                                    style.RED + "\n                           -------------------------------------------------\n"
                                                "                             FAILURE ! Plese check your wallet. \n"
                                                "                            Cause of failure can be : \n"
                                                "                            - GASLIMIT too low\n"
                                                "                            - SLIPPAGE too low\n"
                                                "                           -------------------------------------------------\n\n")
                                print(style.RESET + "")
                                failedtransactionsamount += 1
                                preapprove(tokens)
                            else:
                                # transaction is a SUCCESS
                                print(
                                    style.GREEN + "                           ----------------------------------\n"
                                                    "                           SUCCESS : your Tx is confirmed :)\n"
                                                    "                           ----------------------------------\n")
                                print(style.RESET + "")
                                pass

                    #
                    # SELL CHECK
                    #   If there are already more than MAX_TOKENS in the user's wallet, check to see if we should sell them.
                    #
                    elif token['_REACHED_MAX_TOKENS'] == True and (quote > Decimal(token['SELLPRICEINBASE']) or quote < Decimal(token['STOPLOSSPRICEINBASE'])):

                        if token['_INFORMED_SELL'] == False:
                            printt_info("You own more tokens than your MAXTOKENS parameter for",token['SYMBOL'], " Selling this position")
                            token['_INFORMED_SELL'] = True

                        
                        moonbag = int(Decimal(token['MOONBAG']) * DECIMALS)
                        balance = int(Decimal(balance - moonbag))

                        if balance > 0:
                            print(timestamp(), "Sell Signal Found " + token['SYMBOL'])
                            log_price = "{:.18f}".format(quote)
                            logging.info("Sell Signal Found @" + str(log_price))
                            tx = sell(token['SELLAMOUNTINTOKENS'], token['MOONBAG'], inToken, outToken,
                                        token['GAS'], token['SLIPPAGE'], token['GASLIMIT'], token['BOOSTPERCENT'],
                                        token["HASFEES"], token['USECUSTOMBASEPAIR'], token['SYMBOL'],
                                        token['LIQUIDITYINNATIVETOKEN'])
                            wait_for_tx(tx, token['ADDRESS'])
                            print(
                                style.RESET + "\n                           --------------------------------------\n"
                                                "                            √  Tx done. Check your wallet \n"
                                                "                           --------------------------------------")
                            sleep(3)
                            check_balance(token['ADDRESS'], token['SYMBOL'])
                            print(style.RESET + "\n")
                            sleep(3)

            sleep(cooldown)

    except Exception as ee:
        print(timestamp(), "ERROR. Please go to /log folder and open your error logs : you will find more details.")
        logging.exception(ee)
        logger1.exception(ee)
        sleep(10)
        print("Restarting LimitSwap")
        logging.info("Restarting LimitSwap")
        # Cooldown Logic
        timeout = 10
        nonce = 0
        while True:
            print(".........Restart Cooldown left " + str(timeout - nonce) + " seconds.............")
            nonce += 1
            sleep(1)
            if nonce > timeout:
                run()


try:
    
    # Get the user password on first run
    userpassword = get_password()

    # Handle any proccessing that is necessary to load the private key for the wallet
    parse_wallet_settings(settings, userpassword)

    # The LIMIT balance of the user.
    true_balance = auth()

    version = 3.44
    logging.info("YOUR BOT IS CURRENTLY RUNNING VERSION " + str(version))
    print("YOUR BOT IS CURRENTLY RUNNING VERSION " + str(version))
    check_release()

    if true_balance >= 50:
        print(timestamp(), "Professional Subscriptions Active")
        cooldown = 0.01
        run()

    elif true_balance >= 25 and true_balance < 50:
        print(timestamp(), "Trader Subscriptions Active")
        cooldown = 3
        run()
    elif true_balance >= 10 and true_balance < 25:
        print(timestamp(), "Casual Subscriptions Active")
        cooldown = 6
        run()
    else:
        print(timestamp(),
              "10 - 50 $LIMIT tokens needed to use this bot, please visit the LimitSwap.com for more info or buy more tokens on Uniswap to use!")
        logging.exception(
            "10 - 50 $LIMIT tokens needed to use this bot, please visit the LimitSwap.com for more info or buy more tokens on Uniswap to use!")


except Exception as e:
    print(timestamp(), "ERROR. Please go to /log folder and open your error logs : you will find more details.")
    logging.exception(e)
    logger1.exception(e)
    print("Restarting LimitSwap")
    logging.info("Restarting LimitSwap")
    # Cooldown Logic
    timeout = 10
    nonce = 0
    while True:
        print(".........Restart Cooldown left " + str(timeout - nonce) + " seconds.............")
        nonce += 1
        sleep(1)
        if nonce > timeout:
            run()
