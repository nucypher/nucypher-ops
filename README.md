`pip3 install -e .`
`nucypher-ops nodes create --network ibex --count 1 --cloudprovider digitialocean`
`nucypher-ops ursula deploy --eth-provider https://rinkeby.infura.io/v3/7c1fc379aba44e1395dc629e4a734554 --nucypher-image nucypher/nucypher:airship  --payment-provider https://polygon-mumbai.infura.io/v3/7c1fc379aba44e1395dc629e4a734554 --network ibex` 
