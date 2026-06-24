# Use a lightweight Node image
FROM node:20-alpine

WORKDIR /app

# Copy package configurations first to optimize layer caching
COPY package*.json ./

# Install project dependencies
RUN npm install

# Copy your frontend source code
COPY . .

# Expose Vite's default dev server port
EXPOSE 5173

# Vite requires the --host flag to accept incoming traffic from outside the container
CMD ["npm", "run", "dev", "--", "--host"]