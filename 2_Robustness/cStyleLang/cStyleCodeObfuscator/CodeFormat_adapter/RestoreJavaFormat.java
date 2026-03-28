import com.github.javaparser.JavaParser;
import com.github.javaparser.ParserConfiguration;
import com.github.javaparser.ParseResult;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.printer.PrettyPrinter;
import com.github.javaparser.printer.configuration.PrettyPrinterConfiguration;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Optional;

public class RestoreJavaFormat {
    public static void main(String[] args) throws Exception {
        // Read Java source code from standard input
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder codeBuilder = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            codeBuilder.append(line).append("\n");
        }
        String code = codeBuilder.toString();

        // Parse the source code with JavaParser
        JavaParser parser = new JavaParser(new ParserConfiguration());
        ParseResult<CompilationUnit> result = parser.parse(code);

        Optional<CompilationUnit> optionalCU = result.getResult();
        if (!optionalCU.isPresent()) {
            System.out.println("Unable to parse the Java code.");
            return;
        }

        CompilationUnit cu = optionalCU.get();

        // Configure formatting rules
        PrettyPrinterConfiguration config = new PrettyPrinterConfiguration();
        config.setIndentSize(4);
        config.setPrintComments(true);
        config.setColumnAlignFirstMethodChain(false);

        PrettyPrinter printer = new PrettyPrinter(config);
        String formatted = printer.print(cu);

        // Output the formatted result
        System.out.println(formatted);
    }
}
