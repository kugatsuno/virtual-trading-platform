# virtual-trading-platform

## About

This is a personal project intended to mimic the functions of a virtual live trading platform. 

Built in Python, Javascript, HTML and CSS, using Flask and Jinja

Stocks data provided for free by IEX. 

## Functions

With this platform, the user can simulate live trading using virtual currency. The user is able to track live prices of stocks listed on major exchanges, and can execute trades to test out their trading strategies.

## Instructions

An account from IEX is needed for this application to run. Head over to [iexcloud.io/cloud-login#/register/](iexcloud.io/cloud-login#/register/) to sign up for a free account.

Once an account is created, head over to [iexcloud.io](iexcloud.io) to generate an API token.

With the token, execute 

```
export API_KEY=value
```

where value is the API token generated.

Start the application with 

```
flask run
```
