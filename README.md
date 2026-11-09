# Práctica 7: desplegar la calculadora completa

### Propósito

Desplegar juntos el frontend, el backend y el CronJob de limpieza de logs en el
namespace `practice-7`. El backend y el Job comparten el PVC
`calculadora-logs`: cada ejecución del Job vacía `api-requests.txt` y guarda un
registro fechado en UTC. El script de monitoreo genera operaciones de suma y
muestra las solicitudes recientes y la última limpieza.

### Archivos

- `calculadora-stack.yaml`: namespace, PVC, Deployments, Services y CronJob.
- `monitor-limpieza.sh`: genera solicitudes y muestra el estado de los logs.

## 1. Construir las imágenes

Desde la raíz del repositorio, construye las imágenes del backend, frontend y
Job.

```bash
docker build -t calculadora-backend:latest ./calculadora-backend
```

```bash
docker build -t calculadora-frontend:latest ./calculadora-frontend
```

```bash
docker build -t calculadora-job:latest ./calculadora-job
```

## 2. Cargar las imágenes en Minikube

Carga las imágenes locales dentro del clúster.

```bash
minikube image load calculadora-backend:latest
```

```bash
minikube image load calculadora-frontend:latest
```

```bash
minikube image load calculadora-job:latest
```

## 3. Habilitar el almacenamiento persistente

El PVC usa la StorageClass `csi-hostpath-sc` de Minikube.

```bash
minikube addons enable csi-hostpath-driver
```

## 4. Desplegar la aplicación

Desde la raíz del repositorio, aplica el manifiesto integrado que crea el
namespace y todos los recursos de la práctica.

```bash
kubectl apply -f practice-7/calculadora-stack.yaml
```

## 5. Esperar los Deployments

Espera hasta que el backend y el frontend estén disponibles.

```bash
kubectl rollout status deployment/calculadora-backend -n practice-7
```

```bash
kubectl rollout status deployment/calculadora-frontend -n practice-7
```

## 6. Verificar los recursos

Comprueba que los Pods estén ejecutándose, que el PVC esté enlazado y que el
CronJob esté creado.

```bash
kubectl get pods,pvc,services,cronjobs -n practice-7
```

El CronJob se ejecuta cada cinco minutos, según el horario UTC
`*/5 * * * *`.

## 7. Abrir la calculadora

Mantén el proceso abierto y visita `http://localhost:3000` en el navegador.

```bash
kubectl port-forward service/calculadora-frontend 3000:80 -n practice-7
```

## 8. Abrir el acceso al backend

En otra terminal, mantén el proceso abierto para que el script de monitoreo
pueda enviar solicitudes directamente al backend.

```bash
kubectl port-forward service/calculadora-backend 8080:8080 -n practice-7
```

## 9. Generar solicitudes y observar la limpieza

Desde la raíz del repositorio, ejecuta el script en otra terminal. El segundo
argumento es el intervalo entre peticiones, en segundos.

```bash
chmod +x practice-7/monitor-limpieza.sh
```

```bash
./practice-7/monitor-limpieza.sh
```

Para cambiar la URL del backend o el intervalo:

```bash
./practice-7/monitor-limpieza.sh http://localhost:8080 2
```

El script muestra las respuestas de las operaciones, las últimas líneas de
`api-requests.txt` y el registro de limpieza más reciente. Al ejecutarse el
CronJob, el archivo activo aparecerá vacío; las solicitudes posteriores
volverán a llenarlo. Pulsa Ctrl+C para detener el monitoreo.

## 10. Verificar los Jobs y sus logs

Lista las ejecuciones del CronJob y consulta los logs de una ejecución
reemplazando `<nombre-del-job>` por el nombre mostrado por `kubectl get jobs`.

```bash
kubectl get cronjobs,jobs -n practice-7
```

```bash
kubectl logs job/<nombre-del-job> -n practice-7
```

## 11. Limpiar la práctica

Elimina el namespace y todos los recursos asociados.

```bash
kubectl delete namespace practice-7
```
