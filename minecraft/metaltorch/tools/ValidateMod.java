import net.fabricmc.loader.impl.metadata.*;
import net.fabricmc.loader.api.metadata.ModDependency;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

public class ValidateMod {
  public static void main(String[] a) throws Exception {
    Path jar = Paths.get(a[0]);
    byte[] meta;
    try (ZipFile z = new ZipFile(jar.toFile())) {
      meta = z.getInputStream(z.getEntry("fabric.mod.json")).readAllBytes();
    }
    List<String> warnings = new ArrayList<>();
    LoaderModMetadata m = ModMetadataParser.parseMetadata(
        new java.io.ByteArrayInputStream(meta), jar.toString(), warnings,
        new VersionOverrides(), new DependencyOverrides(Paths.get(".")), false);
    System.out.println("PARSED by fabric-loader's own parser:");
    System.out.println("  id          : " + m.getId());
    System.out.println("  version     : " + m.getVersion());
    System.out.println("  name        : " + m.getName());
    System.out.println("  environment : " + m.getEnvironment());
    System.out.println("  entrypoints : " + m.getEntrypointKeys());
    for (String k : m.getEntrypointKeys())
      for (Object e : m.getEntrypoints(k))
        System.out.println("      " + k + " -> " + e);
    System.out.println("  depends     :");
    for (ModDependency d : m.getDependencies())
      System.out.println("      " + d.getKind() + " " + d.getModId() + " " + d);
    System.out.println("  warnings    : " + (warnings.isEmpty() ? "none" : warnings));
    if (!warnings.isEmpty()) System.exit(1);
  }
}
