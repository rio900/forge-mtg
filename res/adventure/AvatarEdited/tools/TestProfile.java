import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Properties;

/** Validate the disposable profile before Forge initializes its writable directories. */
final class TestProfile {
    static void require() throws IOException {
        var root=Path.of("").toRealPath();
        var profile=new Properties();
        try(var in=Files.newInputStream(root.resolve("forge.profile.properties"))){profile.load(in);}
        for(String key:List.of("userDir","cacheDir","decksDir")){
            var value=profile.getProperty(key);
            if(value==null || !Path.of(value).toRealPath().startsWith(root))
                throw new IOException("Use an isolated Forge profile: "+key);
        }
        if(!Path.of(System.getProperty("user.home")).toRealPath().startsWith(root))
            throw new IOException("Set -Duser.home to the test home");
    }
}
