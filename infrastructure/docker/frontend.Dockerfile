FROM node:20-alpine

WORKDIR /app

# Copy package list and install node dependencies
COPY frontend/package.json ./frontend/
WORKDIR /app/frontend
RUN npm install

# Copy frontend source and shared folder
COPY frontend/ /app/frontend
COPY shared/ /app/shared

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "run", "dev"]
