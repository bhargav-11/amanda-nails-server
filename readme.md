docker build -t amanda-nails-server .
docker run -d -p 5000:5000 amanda-nails-server
