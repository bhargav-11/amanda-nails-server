docker build -t amanda-nails-server .
docker run -d -p 80:5000 amanda-nails-server
