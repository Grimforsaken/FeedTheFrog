package org.gradle.wrapper;

import java.io.*;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/**
 * Tiny transparent bootstrap used only because this generated project cannot
 * bundle Gradle's official wrapper JAR from this environment. It downloads the
 * distribution URL declared in gradle-wrapper.properties and launches Gradle.
 */
public final class GradleWrapperMain {
    public static void main(String[] args) throws Exception {
        Path project = Paths.get(System.getProperty("user.dir"));
        Path propsPath = project.resolve("gradle/wrapper/gradle-wrapper.properties");
        Properties props = new Properties();
        try (InputStream in = Files.newInputStream(propsPath)) { props.load(in); }
        String url = props.getProperty("distributionUrl");
        if (url == null || url.isBlank()) throw new IllegalStateException("distributionUrl missing");

        String file = url.substring(url.lastIndexOf('/') + 1);
        String dirName = file.replace("-bin.zip", "").replace("-all.zip", "");
        Path home = Paths.get(System.getProperty("user.home"), ".gradle", "wrapper", "dists", "feed-the-frog", dirName);
        Path gradleDir = home.resolve(dirName);
        Path exe = gradleDir.resolve("bin").resolve(isWindows() ? "gradle.bat" : "gradle");

        if (!Files.exists(exe)) {
            Files.createDirectories(home);
            Path zip = home.resolve(file);
            if (!Files.exists(zip)) download(url, zip);
            unzip(zip, home);
            if (!Files.exists(exe)) throw new IllegalStateException("Gradle executable not found after extraction: " + exe);
            if (!isWindows()) exe.toFile().setExecutable(true);
        }

        List<String> cmd = new ArrayList<>();
        cmd.add(exe.toAbsolutePath().toString());
        cmd.addAll(Arrays.asList(args));
        ProcessBuilder pb = new ProcessBuilder(cmd).directory(project.toFile()).inheritIO();
        int code = pb.start().waitFor();
        System.exit(code);
    }

    private static void download(String url, Path out) throws Exception {
        System.out.println("Downloading Gradle from " + url);
        HttpClient client = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.ALWAYS).build();
        HttpRequest request = HttpRequest.newBuilder(URI.create(url)).GET().build();
        HttpResponse<Path> response = client.send(request, HttpResponse.BodyHandlers.ofFile(out));
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            Files.deleteIfExists(out);
            throw new IOException("Gradle download failed: HTTP " + response.statusCode());
        }
    }

    private static void unzip(Path zip, Path dest) throws IOException {
        try (ZipInputStream zin = new ZipInputStream(Files.newInputStream(zip))) {
            ZipEntry entry;
            while ((entry = zin.getNextEntry()) != null) {
                Path out = dest.resolve(entry.getName()).normalize();
                if (!out.startsWith(dest)) throw new IOException("Unsafe zip entry: " + entry.getName());
                if (entry.isDirectory()) {
                    Files.createDirectories(out);
                } else {
                    Files.createDirectories(out.getParent());
                    Files.copy(zin, out, StandardCopyOption.REPLACE_EXISTING);
                }
                zin.closeEntry();
            }
        }
    }

    private static boolean isWindows() {
        return System.getProperty("os.name", "").toLowerCase(Locale.ROOT).contains("win");
    }
}
