from appSetup import (getConf, createApp, initAppAddOns, initInfra, initMiddlewares,
                      initViews)
from config.flaskConfig import *
from dotenv import load_dotenv

load_dotenv()
conf = getConf()

# Initialize MongoDB and Redis for session before creating app to avoid circular import issues
sessionRedis, mongoClient = initInfra(conf)
app = createApp(conf)

passwordHasher, limiter = initAppAddOns(app, sessionRedis, conf)

# Finally, initialize middleware and routes
initMiddlewares(app)
initViews(app, sessionRedis, mongoClient, passwordHasher, limiter, conf)


if __name__ == "__main__":
    app.run(port=conf.PORT)