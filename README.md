# SelahSearch API
*SelahSearch* is a Christian API designed to help Christian churches choose theologically-relevant worship songs for their church services (ones that best relate to the sermon passage). This API uses NLP, comparing similarity scores to determine matching themes in both worship song lyrics and passages directly from the bible. This is the backend API Gateway, with the main NLP worker logic deployed to huggingface in a separate repo.

[Access the deployed URL here](https://selahsearch.onrender.com)
*This service was deployed using Render*

## Preparation
If you would like to run a developer version, firstly, ensure you create a fork of the repository and clone it. Ensure you have `npm` installed.

Then run the following commands:

`npm install`

And then run

`npm start`

to run a local version of the backend.

## Environment Variables

In order to fully run the backend locally, you must also have `.env` file setup in the root directory, with the following contents:
- `PORT=3000` the port to run the backend on. Do not use port 8000 if you are also running the NLP worker locally
- `HF_SPACE_URL=<huggingface-space-URL>` the URL of the NLP worker, set to http://localhost:8000 if working locally
- `HF_TOKEN=<your-huggingface-token>` your access token for both the huggingface NLP worker and its transformer model. You should generate one for your account

## Acknowledgements

This project was made by myself and myself only. Various tutorials were used to develop the basics of the NLP model before adapting it to the needs of this API. The lyrics have been scraped manually, directly from each artist listed below. Deployment of this service to a production environment is sadly prohibited unless a formal license to use lyrics for copyrighted songs is acquired. 

The following artists have copyrighted song lyrics used by this API:
- Hillsong Worship
- CityAlight
- Emu Music
- Sovereign Grace
- Keith & Kristen Getty
- Matt Boswell & Matt Papa
- Paul Baloche
- Shane & Shane
- Phil Wickham
- Matt Redman
- Ben Fielding
- Trevor Hodge
- Vertical Worship
- North Point Worship
- We the Kingdom
- Dustin Kensrue
- Steward Towend
- Brooke Lightwood
- Chris Tomlin
