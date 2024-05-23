FROM bellsoft/liberica-runtime-container:jdk-21-slim-musl
COPY ./docker/java/ThetaTerminal.jar /opt/app/ThetaTerminal.jar
EXPOSE 8080
CMD ["java", "-showversion", "-jar", "/opt/app/ThetaTerminal.jar"]
